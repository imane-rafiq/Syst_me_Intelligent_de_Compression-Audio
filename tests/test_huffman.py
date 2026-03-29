"""Tests for the Huffman coding module."""

import pytest
from collections import Counter

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.huffman import HuffmanCoder


class TestHuffmanCoder:
    """Unit tests for HuffmanCoder."""

    def setup_method(self):
        self.coder = HuffmanCoder()

    # ------------------------------------------------------------------
    # Roundtrip tests
    # ------------------------------------------------------------------

    def test_roundtrip_simple(self):
        data = [1, 2, 2, 3, 3, 3, 4, 4, 4, 4]
        bitstring, tree = self.coder.encode(data)
        decoded = self.coder.decode(bitstring, tree)
        assert decoded == data

    def test_roundtrip_single_symbol(self):
        """Edge case: only one unique symbol."""
        data = [7, 7, 7, 7]
        bitstring, tree = self.coder.encode(data)
        decoded = self.coder.decode(bitstring, tree)
        assert decoded == data

    def test_roundtrip_two_symbols(self):
        data = [0, 1, 0, 1, 1, 0]
        bitstring, tree = self.coder.encode(data)
        decoded = self.coder.decode(bitstring, tree)
        assert decoded == data

    def test_roundtrip_large(self):
        import random
        random.seed(42)
        data = [random.randint(-10, 10) for _ in range(1_000)]
        bitstring, tree = self.coder.encode(data)
        decoded = self.coder.decode(bitstring, tree)
        assert decoded == data

    def test_roundtrip_negative_symbols(self):
        data = [-3, -2, -1, 0, 1, 2, 3, -3, 0]
        bitstring, tree = self.coder.encode(data)
        decoded = self.coder.decode(bitstring, tree)
        assert decoded == data

    def test_roundtrip_string_symbols(self):
        data = list("abracadabra")
        bitstring, tree = self.coder.encode(data)
        decoded = self.coder.decode(bitstring, tree)
        assert decoded == data

    # ------------------------------------------------------------------
    # Empty input
    # ------------------------------------------------------------------

    def test_empty_input(self):
        bitstring, tree = self.coder.encode([])
        assert bitstring == ""
        assert tree is None
        decoded = self.coder.decode("", None)
        assert decoded == []

    # ------------------------------------------------------------------
    # Prefix-free property
    # ------------------------------------------------------------------

    def test_prefix_free_codebook(self):
        """No codeword should be a prefix of another."""
        data = [1, 2, 2, 3, 3, 3, 4]
        codebook = self.coder.build_codebook(data)
        codes = list(codebook.values())
        for i, c1 in enumerate(codes):
            for j, c2 in enumerate(codes):
                if i != j:
                    assert not c2.startswith(c1), (
                        f"Codeword '{c1}' is a prefix of '{c2}'"
                    )

    # ------------------------------------------------------------------
    # Compression property
    # ------------------------------------------------------------------

    def test_compression_is_beneficial(self):
        """Huffman-encoded data should be shorter than 8-bit fixed coding."""
        import random
        random.seed(0)
        # Heavily skewed distribution
        data = [0] * 900 + [1] * 80 + [2] * 15 + [3] * 5
        random.shuffle(data)
        bitstring, _ = self.coder.encode(data)
        fixed_bits = len(data) * 8
        assert len(bitstring) < fixed_bits, (
            "Huffman encoding should outperform fixed-width coding for skewed data"
        )

    # ------------------------------------------------------------------
    # Codebook tests
    # ------------------------------------------------------------------

    def test_codebook_keys_match_symbols(self):
        data = [10, 20, 30, 10, 20, 10]
        codebook = self.coder.build_codebook(data)
        assert set(codebook.keys()) == {10, 20, 30}

    def test_codebook_most_frequent_shortest(self):
        """Most frequent symbol should have the shortest code."""
        data = [1] * 100 + [2] * 10 + [3]
        codebook = self.coder.build_codebook(data)
        assert len(codebook[1]) <= len(codebook[2])
        assert len(codebook[2]) <= len(codebook[3])
