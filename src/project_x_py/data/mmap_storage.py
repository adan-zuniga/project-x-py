"""
Memory-mapped file storage for efficient large data handling.

This module provides memory-mapped file storage for large datasets,
allowing efficient access to data without loading everything into RAM.
"""

import logging
import mmap
import pickle
import tempfile
import threading
from io import BufferedRandom, BufferedReader
from pathlib import Path
from typing import Any, cast

import numpy as np
import polars as pl

logger = logging.getLogger(__name__)


class MemoryMappedStorage:
    """
    Efficient storage for large datasets using memory-mapped files.

    Features:
        - Direct disk access without loading entire dataset into memory
        - Efficient slice reading and writing
        - Support for NumPy arrays and Polars DataFrames
        - Automatic file management and cleanup
        - Thread-safe operations
    """

    def __init__(self, filename: str | Path, mode: str = "r+b"):
        """
        Initialize memory-mapped storage.

        Args:
            filename: Path to the storage file
            mode: File mode ('r+b' for read/write, 'rb' for read-only)
        """
        self.filename = Path(filename)
        self.mode = mode
        self.fp: BufferedRandom | BufferedReader | None = None
        self.mmap: mmap.mmap | None = None
        self._metadata: dict[str, Any] = {}
        self._file_size = 1024 * 1024 * 10  # Start with 10MB
        self._data_file_size = 0
        self._lock = threading.RLock()

    def __enter__(self) -> "MemoryMappedStorage":
        """Context manager entry."""
        self.open()
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    def open(self) -> None:
        """Open the memory-mapped file."""
        with self._lock:
            if self.fp is not None:
                return

            # Create file if it doesn't exist (unless read-only)
            if not self.filename.exists() and ("+" in self.mode or "w" in self.mode):
                self.filename.parent.mkdir(parents=True, exist_ok=True)
                # Pre-allocate file with initial size
                with open(self.filename, "wb") as f:
                    f.write(b"\x00" * self._file_size)

            self.fp = cast(
                BufferedRandom | BufferedReader,
                open(self.filename, self.mode),  # noqa: SIM115
            )
            # Note: open() either succeeds or raises an exception, so fp is never None

            # Get file size
            self.fp.seek(0, 2)  # Seek to end
            size = self.fp.tell()
            self._data_file_size = size

            if size == 0 and ("+" in self.mode or "w" in self.mode):
                # Initialize empty file with default size
                self.fp.write(b"\x00" * self._file_size)
                self.fp.flush()
                self.fp.seek(0)
                size = self._file_size
                self._data_file_size = size

            if size > 0:
                # Use ACCESS_READ for read-only mode
                access = (
                    mmap.ACCESS_READ
                    if "r" in self.mode and "+" not in self.mode
                    else mmap.ACCESS_DEFAULT
                )
                if self.fp:
                    self.mmap = mmap.mmap(self.fp.fileno(), 0, access=access)

    def close(self) -> None:
        """Close the memory-mapped file."""
        with self._lock:
            if self.mmap:
                self.mmap.close()
                self.mmap = None
            if self.fp:
                self.fp.close()
                self.fp = None

    def _resize_file(self, new_size: int) -> None:
        """Resize the file and recreate mmap (for macOS compatibility)."""
        # This method should be called within a lock
        if self.mmap:
            self.mmap.close()

        if self.fp is None:
            raise ValueError("File pointer is None")

        self.fp.truncate(new_size)
        self.fp.flush()

        access = (
            mmap.ACCESS_READ
            if "r" in self.mode and "+" not in self.mode
            else mmap.ACCESS_DEFAULT
        )
        self.mmap = mmap.mmap(self.fp.fileno(), 0, access=access)
        self._data_file_size = new_size

    def write_array(self, data: np.ndarray, offset: int = 0) -> int:
        """
        Write NumPy array to memory-mapped file.

        Args:
            data: NumPy array to write
            offset: Byte offset in file

        Returns:
            Number of bytes written
        """
        with self._lock:
            if not self.mmap:
                self.open()

            if not self.mmap:
                raise OSError("Memory map not available")

            # Serialize array metadata
            metadata = {"dtype": str(data.dtype), "shape": data.shape, "offset": offset}

            # Convert to bytes
            data_bytes = data.tobytes()
            metadata_bytes = pickle.dumps(metadata)  # nosec B301 - internal data only

            # Write metadata size (4 bytes), metadata, then data
            size_bytes = len(metadata_bytes).to_bytes(4, "little")

            # Check if we need more space
            total_size = offset + 4 + len(metadata_bytes) + len(data_bytes)
            if total_size > self._data_file_size:
                # On macOS, we can't resize mmap, so we need to recreate it
                self._resize_file(total_size)

            # Write to mmap
            self.mmap[offset : offset + 4] = size_bytes
            self.mmap[offset + 4 : offset + 4 + len(metadata_bytes)] = metadata_bytes
            self.mmap[offset + 4 + len(metadata_bytes) : total_size] = data_bytes
            self.mmap.flush()

            return total_size - offset

    def read_array(self, offset: int = 0) -> np.ndarray | None:
        """
        Read NumPy array from memory-mapped file.

        Args:
            offset: Byte offset in file

        Returns:
            NumPy array or None if not found
        """
        with self._lock:
            if not self.mmap:
                self.open()

            if not self.mmap:
                return None

            try:
                # Read metadata size
                size_bytes = self.mmap[offset : offset + 4]
                metadata_size = int.from_bytes(size_bytes, "little")

                # Read metadata
                metadata_bytes = self.mmap[offset + 4 : offset + 4 + metadata_size]
                metadata = pickle.loads(metadata_bytes)  # nosec B301 - internal data only

                # Calculate data size
                dtype = np.dtype(metadata["dtype"])
                shape = metadata["shape"]
                data_size = dtype.itemsize * np.prod(shape)

                # Read data
                data_start = offset + 4 + metadata_size
                data_bytes = self.mmap[data_start : data_start + data_size]

                # Convert to array
                array = np.frombuffer(data_bytes, dtype=dtype).reshape(shape)
                return array.copy()  # Return copy to avoid mmap issues

            except Exception:
                logger.exception("Error reading array at offset %d", offset)
                return None

    def _load_metadata(self) -> None:
        # should be called within a lock
        if not self._metadata:
            metadata_file = self.filename.with_suffix(".meta")
            if metadata_file.exists():
                try:
                    with open(metadata_file, "rb") as f:
                        self._metadata = pickle.load(f)  # nosec B301 - internal data only
                except (pickle.UnpicklingError, EOFError):
                    logger.exception(
                        "Could not load metadata from %s, file might be corrupt.",
                        metadata_file,
                    )
                    self._metadata = {}

    def _save_metadata(self) -> None:
        # should be called within a lock
        metadata_file = self.filename.with_suffix(".meta")
        # Safe save: write to temp file then rename
        with tempfile.NamedTemporaryFile(
            "wb", delete=False, dir=metadata_file.parent
        ) as tmp_f:
            pickle.dump(self._metadata, tmp_f)  # nosec B301 - internal data only
            tmp_path = Path(tmp_f.name)

        tmp_path.rename(metadata_file)

    def write_dataframe(self, df: pl.DataFrame, key: str = "default") -> bool:
        """
        Write Polars DataFrame to memory-mapped storage.

        Args:
            df: Polars DataFrame to store
            key: Storage key for the DataFrame

        Returns:
            Success status
        """
        with self._lock:
            try:
                if not self.mmap:
                    self.open()

                # Load existing metadata if present
                self._load_metadata()

                # Calculate starting offset (after existing data)
                offset = self._data_file_size

                # Convert DataFrame to dict format
                data: dict[str, Any] = {
                    "schema": {name: str(dtype) for name, dtype in df.schema.items()},
                    "columns": {},
                    "shape": df.shape,
                    "key": key,
                }

                # Store each column as NumPy array
                col_offset = offset
                for col_name in df.columns:
                    col_data = df[col_name].to_numpy()
                    bytes_written = self.write_array(col_data, col_offset)
                    data["columns"][col_name] = {
                        "offset": col_offset,
                        "size": bytes_written,
                    }
                    col_offset += bytes_written

                # Store metadata
                self._metadata[key] = data
                self._save_metadata()

                # Update data file size tracker
                self._data_file_size = col_offset

                return True

            except Exception:
                logger.exception("Error writing DataFrame with key '%s'", key)
                return False

    def read_dataframe(self, key: str = "default") -> pl.DataFrame | None:
        """
        Read Polars DataFrame from memory-mapped storage.

        Args:
            key: Storage key for the DataFrame

        Returns:
            Polars DataFrame or None if not found
        """
        with self._lock:
            try:
                # Load metadata if not already loaded
                self._load_metadata()

                if key not in self._metadata:
                    return None

                metadata = self._metadata[key]

                # Read each column
                columns = {}
                for col_name, col_info in metadata["columns"].items():
                    array = self.read_array(col_info["offset"])
                    if array is not None:
                        columns[col_name] = array

                # Reconstruct DataFrame
                return pl.DataFrame(columns)

            except Exception:
                logger.exception("Error reading DataFrame with key '%s'", key)
                return None

    def get_info(self) -> dict[str, Any]:
        """
        Get information about the storage file.

        Returns:
            Dictionary with storage information
        """
        with self._lock:
            # Load metadata if not already loaded
            self._load_metadata()

            info = {
                "filename": str(self.filename),
                "exists": self.filename.exists(),
                "size_mb": 0,
                "keys": list(self._metadata.keys()),
            }

            if self.filename.exists():
                info["size_mb"] = self.filename.stat().st_size / (1024 * 1024)

            return info


class TimeSeriesStorage(MemoryMappedStorage):
    """
    Specialized memory-mapped storage for time series data.

    Optimized for append-only time series with efficient windowing.
    """

    def __init__(
        self, filename: str | Path, columns: list[str], dtype: type = np.float64
    ):
        """
        Initialize time series storage.

        Args:
            filename: Path to the storage file
            columns: Column names for the time series
            dtype: Data type for storage
        """
        super().__init__(filename, "r+b")
        self.columns = columns
        self.dtype = np.dtype(dtype)
        self.row_size = (len(self.columns) + 1) * self.dtype.itemsize
        self.current_size = 0

        # Load metadata to get actual data size if file exists
        if self.filename.exists():
            self.open()  # open() is idempotent and thread-safe
            self._load_metadata()
            # Get current_size from metadata if available
            if "_timeseries_meta" in self._metadata:
                self.current_size = self._metadata["_timeseries_meta"].get(
                    "current_size", 0
                )

    def append_data(self, timestamp: float, values: dict[str, float]) -> bool:
        """
        Append a new row to the time series.

        Args:
            timestamp: Unix timestamp
            values: Dictionary of column values

        Returns:
            Success status
        """
        with self._lock:
            try:
                if not self.mmap:
                    self.open()

                if not self.mmap:
                    raise OSError("Memory map not available")

                # Create row array
                row: np.ndarray = np.zeros(len(self.columns) + 1, dtype=self.dtype)
                row[0] = timestamp

                for i, col in enumerate(self.columns):
                    if col in values:
                        row[i + 1] = values[col]

                # Calculate offset
                offset = self.current_size * self.row_size

                # Check if we need more space
                if offset + self.row_size > self._data_file_size:
                    new_size = max(offset + self.row_size, self._data_file_size * 2)
                    self._resize_file(new_size)

                # Write row directly to mmap
                if self.mmap:
                    self.mmap[offset : offset + self.row_size] = row.tobytes()
                    self.mmap.flush()
                self.current_size += 1

                # Update metadata with current size
                self._metadata["_timeseries_meta"] = {"current_size": self.current_size}
                self._save_metadata()

                return True

            except Exception:
                logger.exception("Error appending data")
                return False

    def _get_row(self, index: int) -> np.ndarray | None:
        """Reads a single row by index."""
        if not self.mmap or index < 0 or index >= self.current_size:
            return None

        offset = index * self.row_size
        if offset + self.row_size > len(self.mmap):
            return None

        row_bytes = self.mmap[offset : offset + self.row_size]
        return np.frombuffer(row_bytes, dtype=self.dtype, count=len(self.columns) + 1)

    def read_window(self, start_time: float, end_time: float) -> pl.DataFrame | None:
        """
        Read data within a time window.

        Args:
            start_time: Start timestamp
            end_time: End timestamp

        Returns:
            DataFrame with data in the window
        """
        with self._lock:
            try:
                if not self.mmap:
                    self.open()

                if not self.mmap or self.current_size == 0:
                    return None

                # Binary search to find the first row >= start_time
                low, high = 0, self.current_size - 1
                start_index = self.current_size

                while low <= high:
                    mid = (low + high) // 2
                    row = self._get_row(mid)
                    if row is not None and row[0] >= start_time:
                        start_index = mid
                        high = mid - 1
                    elif row is not None:
                        low = mid + 1
                    else:  # Should not happen in this loop
                        break

                if start_index >= self.current_size:
                    return None  # No data in the window

                # Read data sequentially from start_index
                all_data = []
                for i in range(start_index, self.current_size):
                    row = self._get_row(i)
                    if row is not None:
                        if row[0] > end_time:
                            break
                        all_data.append(row)

                if not all_data:
                    return None

                # Convert to DataFrame
                data_array = np.vstack(all_data)
                df_dict = {"timestamp": data_array[:, 0]}

                for i, col in enumerate(self.columns):
                    df_dict[col] = data_array[:, i + 1]

                return pl.DataFrame(df_dict)

            except Exception:
                logger.exception(
                    "Error reading window from %f to %f", start_time, end_time
                )
                return None
