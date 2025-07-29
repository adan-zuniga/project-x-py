"""Test contract selection logic"""

from unittest.mock import Mock

import pytest

from project_x_py.client import ProjectX


class TestContractSelection:
    """Test the _select_best_contract method"""

    def test_select_best_contract_exact_name_match(self):
        """Test exact name matching after removing futures suffix"""
        client = ProjectX(api_key="test", username="test")

        # Test data with various contract naming patterns
        contracts = [
            {
                "id": "CON.F.US.ENQ.U25",
                "name": "NQU5",
                "symbolId": "F.US.ENQ",
                "activeContract": True,
            },
            {
                "id": "CON.F.US.MNQ.U25",
                "name": "MNQU5",
                "symbolId": "F.US.MNQ",
                "activeContract": True,
            },
        ]

        # Should select ENQ when searching for "NQ"
        result = client._select_best_contract(contracts, "NQ")
        assert result["symbolId"] == "F.US.ENQ"
        assert result["name"] == "NQU5"

    def test_select_best_contract_with_double_digit_year(self):
        """Test contracts with 2-digit year codes"""
        client = ProjectX(api_key="test", username="test")

        contracts = [
            {
                "id": "CON.F.US.MGC.H25",
                "name": "MGCH25",
                "symbolId": "F.US.MGC",
                "activeContract": True,
            },
            {
                "id": "CON.F.US.MGC.M25",
                "name": "MGCM25",
                "symbolId": "F.US.MGC",
                "activeContract": False,
            },
        ]

        # Should match MGCH25 when searching for "MGC"
        result = client._select_best_contract(contracts, "MGC")
        assert result["name"] == "MGCH25"

    def test_select_best_contract_symbol_id_match(self):
        """Test symbolId suffix matching"""
        client = ProjectX(api_key="test", username="test")

        contracts = [
            {
                "id": "CON.F.US.CL.F25",
                "name": "CLF25",
                "symbolId": "F.US.CL",
                "activeContract": True,
            },
            {
                "id": "CON.F.US.QCL.F25",
                "name": "QCLF25",
                "symbolId": "F.US.QCL",
                "activeContract": True,
            },
        ]

        # Should match F.US.CL when searching for "CL"
        result = client._select_best_contract(contracts, "CL")
        assert result["symbolId"] == "F.US.CL"

    def test_select_best_contract_priority_order(self):
        """Test selection priority order"""
        client = ProjectX(api_key="test", username="test")

        contracts = [
            # Inactive exact match
            {
                "id": "1",
                "name": "NQZ24",
                "symbolId": "F.US.ENQ",
                "activeContract": False,
            },
            # Active but not exact match
            {
                "id": "2",
                "name": "MNQU5",
                "symbolId": "F.US.MNQ",
                "activeContract": True,
            },
            # Active exact match (should be selected)
            {"id": "3", "name": "NQU5", "symbolId": "F.US.ENQ", "activeContract": True},
        ]

        result = client._select_best_contract(contracts, "NQ")
        assert result["id"] == "3"

    def test_select_best_contract_no_exact_match(self):
        """Test fallback when no exact match exists"""
        client = ProjectX(api_key="test", username="test")

        contracts = [
            {"id": "1", "name": "ESU5", "symbolId": "F.US.ES", "activeContract": False},
            {"id": "2", "name": "ESZ5", "symbolId": "F.US.ES", "activeContract": True},
        ]

        # No exact "ES" name match, should fall back to active contract
        result = client._select_best_contract(contracts, "ES")
        assert result["id"] == "2"  # Active contract

    def test_select_best_contract_empty_list(self):
        """Test handling of empty contract list"""
        client = ProjectX(api_key="test", username="test")

        result = client._select_best_contract([], "NQ")
        assert result is None
