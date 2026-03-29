"""
Huffman Coding Module
======================
Implements Huffman encoding and decoding for lossless compression
of quantized audio coefficients.
"""

import heapq
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass(order=True)
class _HuffmanNode:
    """A node in the Huffman tree."""

    freq: int
    symbol: Any = field(compare=False, default=None)
    left: Optional["_HuffmanNode"] = field(compare=False, default=None)
    right: Optional["_HuffmanNode"] = field(compare=False, default=None)

    @property
    def is_leaf(self) -> bool:
        return self.left is None and self.right is None


class HuffmanCoder:
    """
    Huffman encoder/decoder.

    Builds an optimal prefix-free code from a symbol frequency table
    and uses it to encode/decode sequences.

    Example
    -------
    >>> coder = HuffmanCoder()
    >>> data = [1, 2, 2, 3, 3, 3]
    >>> encoded, tree = coder.encode(data)
    >>> decoded = coder.decode(encoded, tree)
    >>> decoded == data
    True
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def encode(self, data: list) -> Tuple[str, "_HuffmanNode"]:
        """
        Encode *data* using Huffman coding.

        Parameters
        ----------
        data:
            A list of hashable symbols (e.g. integers).

        Returns
        -------
        bitstring:
            A string of '0'/'1' characters representing the encoded data.
        root:
            The root of the Huffman tree required for decoding.
        """
        if not data:
            return "", None

        freq = Counter(data)

        # Edge case: single unique symbol
        if len(freq) == 1:
            symbol = next(iter(freq))
            root = _HuffmanNode(freq=freq[symbol], symbol=symbol)
            bitstring = "0" * len(data)
            return bitstring, root

        root = self._build_tree(freq)
        codebook = self._build_codebook(root)
        bitstring = "".join(codebook[s] for s in data)
        return bitstring, root

    def decode(self, bitstring: str, root: "_HuffmanNode") -> list:
        """
        Decode a *bitstring* using the Huffman tree rooted at *root*.

        Parameters
        ----------
        bitstring:
            String of '0'/'1' characters produced by :meth:`encode`.
        root:
            The Huffman tree root returned by :meth:`encode`.

        Returns
        -------
        list of decoded symbols.
        """
        if root is None:
            return []

        decoded = []
        node = root

        # Single-symbol edge case
        if root.is_leaf:
            return [root.symbol] * len(bitstring)

        for bit in bitstring:
            node = node.left if bit == "0" else node.right
            if node.is_leaf:
                decoded.append(node.symbol)
                node = root

        return decoded

    def build_codebook(self, data: list) -> Dict[Any, str]:
        """
        Return the Huffman codebook (symbol → bitstring) for *data*.

        Parameters
        ----------
        data:
            A list of hashable symbols.

        Returns
        -------
        dict mapping each symbol to its binary codeword.
        """
        freq = Counter(data)
        if len(freq) == 1:
            symbol = next(iter(freq))
            return {symbol: "0"}
        root = self._build_tree(freq)
        return self._build_codebook(root)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_tree(freq: Dict[Any, int]) -> "_HuffmanNode":
        heap = [_HuffmanNode(freq=f, symbol=s) for s, f in freq.items()]
        heapq.heapify(heap)
        while len(heap) > 1:
            lo = heapq.heappop(heap)
            hi = heapq.heappop(heap)
            merged = _HuffmanNode(freq=lo.freq + hi.freq, left=lo, right=hi)
            heapq.heappush(heap, merged)
        return heap[0]

    @staticmethod
    def _build_codebook(root: "_HuffmanNode") -> Dict[Any, str]:
        codebook: Dict[Any, str] = {}

        def _traverse(node: "_HuffmanNode", prefix: str) -> None:
            if node.is_leaf:
                codebook[node.symbol] = prefix if prefix else "0"
                return
            _traverse(node.left, prefix + "0")
            _traverse(node.right, prefix + "1")

        _traverse(root, "")
        return codebook
