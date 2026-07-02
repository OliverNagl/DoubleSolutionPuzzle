"""
MCMC Double-Solution Puzzle Generator

Generates jigsaw puzzles that have exactly two valid solutions by using
Markov Chain Monte Carlo optimization over edge colorings with a fixed mapping.
"""

from .solver import MCMCSolver
from .state import MCMCState
from .mapping import generate_mcmc_mapping
from .convert import mcmc_to_legacy_format, mcmc_to_numpy_solutions

__all__ = [
    "MCMCSolver",
    "MCMCState",
    "generate_mcmc_mapping",
    "mcmc_to_legacy_format",
    "mcmc_to_numpy_solutions",
]
