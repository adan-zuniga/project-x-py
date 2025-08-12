"""
Memory-mapped file storage for efficient large data handling.

This module provides memory-mapped file storage for large datasets,
allowing efficient access to data without loading everything into RAM.
"""

import mmap
import pickle
from io import BufferedRandom, BufferedReader
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl


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

        # Create file if it doesn't exist (unless read-only)
        if not self.filename.exists() and "+" in mode:
            self.filename.parent.mkdir(parents=True, exist_ok=True)
            # Pre-allocate file with initial size
            with open(self.filename, "wb") as f:
                f.write(b"\x00" * self._file_size)

    def __enter__(self) -> "MemoryMappedStorage":
        """Context manager entry."""
        self.open()
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    def open(self) -> None:
        """Open the memory-mapped file."""
        if self.fp is None:
            self.fp = open(self.filename, self.mode)  # type: ignore  # noqa: SIM115

        if self.fp is not None:
            # Get file size
            self.fp.seek(0, 2)  # Seek to end
            size = self.fp.tell()

            if size == 0 and ("+" in self.mode or "w" in self.mode):
                # Initialize empty file with default size
                self.fp.write(b"\x00" * self._file_size)
                self.fp.flush()
                self.fp.seek(0)
                size = self._file_size

            if size > 0:
                # Use ACCESS_READ for read-only mode
                if "r" in self.mode and "+" not in self.mode:
                    self.mmap = mmap.mmap(self.fp.fileno(), 0, access=mmap.ACCESS_READ)
                else:
                    self.mmap = mmap.mmap(self.fp.fileno(), 0)

    def close(self) -> None:
        """Close the memory-mapped file."""
        if self.mmap:
            self.mmap.close()
            self.mmap = None
        if self.fp:
            self.fp.close()
            self.fp = None

    def _resize_file(self, new_size: int) -> None:
        """Resize the file and recreate mmap (for macOS compatibility)."""
        # Close existing mmap
        if self.mmap:
            self.mmap.close()

        if self.fp is None:
            raise ValueError("File pointer is None")

        # Resize the file
        self.fp.seek(0, 2)  # Go to end
        current_size = self.fp.tell()

        if new_size > current_size:
            # Extend the file
            self.fp.write(b"\\x00" * (new_size - current_size))
            self.fp.flush()

        # Recreate mmap with new size
        self.mmap = mmap.mmap(self.fp.fileno(), 0)

    def write_array(self, data: np.ndarray, offset: int = 0) -> int:
        """
        Write NumPy array to memory-mapped file.

        Args:
            data: NumPy array to write
            offset: Byte offset in file

        Returns:
            Number of bytes written
        """
        if not self.mmap:
            self.open()

        # Serialize array metadata
        metadata = {"dtype": str(data.dtype), "shape": data.shape, "offset": offset}

        # Convert to bytes
        data_bytes = data.tobytes()
        metadata_bytes = pickle.dumps(metadata)

        # Write metadata size (4 bytes), metadata, then data
        size_bytes = len(metadata_bytes).to_bytes(4, "little")

        # Check if we need more space
        total_size = offset + 4 + len(metadata_bytes) + len(data_bytes)
        if self.mmap and total_size > len(self.mmap):
            # On macOS, we can't resize mmap, so we need to recreate it
            self._resize_file(total_size)
        elif not self.mmap:
            self.open()
            if self.mmap and total_size > len(self.mmap):
                self._resize_file(total_size)

        # Write to mmap
        if self.mmap:
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
            metadata = pickle.loads(metadata_bytes)

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

        except Exception as e:
            print(f"Error reading array: {e}")
            return None

    def write_dataframe(self, df: pl.DataFrame, key: str = "default") -> bool:
        """
        Write Polars DataFrame to memory-mapped storage.

        Args:
            df: Polars DataFrame to store
            key: Storage key for the DataFrame

        Returns:
            Success status
        """
        try:
            # Load existing metadata if present
            metadata_file = self.filename.with_suffix(".meta")
            if metadata_file.exists():
                with open(metadata_file, "rb") as f:
                    self._metadata = pickle.load(f)

            # Calculate starting offset (after existing data)
            offset = 0
            for existing_key, existing_data in self._metadata.items():
                if existing_key != key and "columns" in existing_data:
                    for col_info in existing_data["columns"].values():
                        offset = max(offset, col_info["offset"] + col_info["size"])

            # Convert DataFrame to dict format
            data: dict[str, Any] = {
                "schema": {name: str(dtype) for name, dtype in df.schema.items()},
                "columns": {},
                "shape": df.shape,
                "key": key,
            }

            # Store each column as NumPy array
            for col_name in df.columns:
                col_data = df[col_name].to_numpy()
                bytes_written = self.write_array(col_data, offset)
                data["columns"][col_name] = {"offset": offset, "size": bytes_written}
                offset += bytes_written

            # Store metadata
            self._metadata[key] = data

            # Write metadata to a separate file
            metadata_file = self.filename.with_suffix(".meta")
            with open(metadata_file, "wb") as f:
                pickle.dump(self._metadata, f)

            return True

        except Exception as e:
            print(f"Error writing DataFrame: {e}")
            return False

    def read_dataframe(self, key: str = "default") -> pl.DataFrame | None:
        """
        Read Polars DataFrame from memory-mapped storage.

        Args:
            key: Storage key for the DataFrame

        Returns:
            Polars DataFrame or None if not found
        """
        try:
            # Load metadata if not already loaded
            if not self._metadata:
                metadata_file = self.filename.with_suffix(".meta")
                if metadata_file.exists():
                    with open(metadata_file, "rb") as f:
                        self._metadata = pickle.load(f)

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

        except Exception as e:
            print(f"Error reading DataFrame: {e}")
            return None

    def get_info(self) -> dict[str, Any]:
        """
        Get information about the storage file.

        Returns:
            Dictionary with storage information
        """
        info = {
            "filename": str(self.filename),
            "exists": self.filename.exists(),
            "size_mb": 0,
            "keys": list(self._metadata.keys()) if self._metadata else [],
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
        self.dtype = dtype
        self.current_size = 0
        self.chunk_size = 10000  # Records per chunk

    def append_data(self, timestamp: float, values: dict[str, float]) -> bool:
        """
        Append a new row to the time series.

        Args:
            timestamp: Unix timestamp
            values: Dictionary of column values

        Returns:
            Success status
        """
        try:
            if not self.mmap:
                self.open()

            # Create row array
            row: np.ndarray = np.zeros(len(self.columns) + 1, dtype=self.dtype)
            row[0] = timestamp

            for i, col in enumerate(self.columns):
                if col in values:
                    row[i + 1] = values[col]

            # Calculate offset
            offset = self.current_size * row.nbytes

            # Check if we need more space
            if self.mmap and offset + row.nbytes > len(self.mmap):
                new_size = max(offset + row.nbytes, len(self.mmap) * 2)
                self._resize_file(new_size)
            elif not self.mmap:
                self.open()
                if self.mmap and offset + row.nbytes > len(self.mmap):
                    new_size = max(offset + row.nbytes, len(self.mmap) * 2)
                    self._resize_file(new_size)

            # Write row directly to mmap
            if self.mmap:
                self.mmap[offset : offset + row.nbytes] = row.tobytes()
                self.mmap.flush()
            self.current_size += 1

            return True

        except Exception as e:
            print(f"Error appending data: {e}")
            return False

    def read_window(self, start_time: float, end_time: float) -> pl.DataFrame | None:
        """
        Read data within a time window.

        Args:
            start_time: Start timestamp
            end_time: End timestamp

        Returns:
            DataFrame with data in the window
        """
        try:
            # Read all data directly from mmap (don't use read_array which expects pickle)
            if not self.mmap:
                self.open()

            if not self.mmap:
                return None

            all_data = []
            row_size = (len(self.columns) + 1) * np.dtype(self.dtype).itemsize

            for i in range(self.current_size):
                offset = i * row_size

                # Read raw bytes and convert to array
                if self.mmap and offset + row_size <= len(self.mmap):
                    row_bytes = self.mmap[offset : offset + row_size]
                    row: np.ndarray = np.frombuffer(
                        row_bytes, dtype=self.dtype, count=len(self.columns) + 1
                    )

                if row is not None and start_time <= row[0] <= end_time:
                    all_data.append(row)

            if not all_data:
                return None

            # Convert to DataFrame
            data_array = np.vstack(all_data)
            df_dict = {"timestamp": data_array[:, 0]}

            for i, col in enumerate(self.columns):
                df_dict[col] = data_array[:, i + 1]

            return pl.DataFrame(df_dict)

        except Exception as e:
            print(f"Error reading window: {e}")
            return None
