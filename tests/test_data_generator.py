import importlib.util
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).parents[1]


def load_generator_module():
    module_path = PROJECT_ROOT / "data-generator" / "generate_transactions.py"
    spec = importlib.util.spec_from_file_location("generate_transactions", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generator():
    return load_generator_module()


class FakeCursor:
    def __init__(self):
        self._rows = []
        self.queries = []
        self._query_index = 0

    def execute(self, query):
        self.queries.append(query)
        if self._query_index == 0:
            self._rows = [(1, "Tier 1"), (2, "tier_2")]
        elif self._query_index == 1:
            self._rows = [(10, "Coffee", 24000, 20000, 16000)]
        elif self._query_index == 2:
            self._rows = [(101, 1), (102, 2)]
        elif self._query_index == 3:
            self._rows = [(201,), (202,)]
        else:
            self._rows = []
        self._query_index += 1

    def fetchall(self):
        return self._rows


def test_normalize_tier_supports_existing_labels(generator):
    assert generator.normalize_tier("Tier 1") == "tier_1"
    assert generator.normalize_tier("tier_2") == "tier_2"
    assert generator.normalize_tier(" Tier 3 ") == "tier_3"


def test_fetch_master_data_returns_valid_employee_and_customer_references(generator):
    cursor = FakeCursor()

    outlets, menus, employees_by_outlet, customer_ids = generator.fetch_master_data(cursor)

    assert outlets == [
        {"id": 1, "tier": "tier_1"},
        {"id": 2, "tier": "tier_2"},
    ]
    assert menus[0]["tier_1"] == 24000
    assert employees_by_outlet == {1: [101], 2: [102]}
    assert customer_ids == [201, 202]


def test_order_and_payment_values_match_dev_enums(generator):
    assert set(generator.ORDER_STATUSES) == {
        "PENDING", "COMPLETED", "CANCELLED", "REFUNDED"
    }
    assert set(generator.PAYMENT_METHODS) == {
        "CASH", "QRIS", "DEBIT_CARD", "CREDIT_CARD", "E_WALLET"
    }
    assert len(generator.PAYMENT_METHODS) == len(generator.PAYMENT_WEIGHTS)


def test_payment_status_mapping_matches_order_statuses(generator):
    mapping = {
        "COMPLETED": "SUCCESS",
        "PENDING": "PENDING",
        "CANCELLED": "FAILED",
        "REFUNDED": "REFUNDED",
    }

    assert set(mapping) == set(generator.ORDER_STATUSES)
    assert set(mapping.values()) == {"SUCCESS", "PENDING", "FAILED", "REFUNDED"}
