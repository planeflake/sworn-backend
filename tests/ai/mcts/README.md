# MCTS Tests

This directory contains tests for the Monte Carlo Tree Search (MCTS) implementation and related state classes.

## Test Structure

- `test_core.py`: Tests for the core MCTS algorithm and node classes
- `test_integration.py`: Integration tests showing MCTS working with actual state implementations
- `states/test_trader_state.py`: Tests for the TraderState implementation
- `states/test_player_state.py`: Tests for the PlayerState implementation

## Running Tests

To run all tests:

```bash
cd sworn-backend
python -m unittest discover -s tests/ai/mcts
```

To run specific test files:

```bash
python -m unittest tests/ai/mcts/test_core.py
python -m unittest tests/ai/mcts/states/test_trader_state.py
```

## Test Coverage

The tests cover:

1. Core MCTS functionality
   - Node initialization and updates
   - Child selection using UCB1
   - Search algorithm with selection, expansion, simulation, and backpropagation

2. State implementations
   - State initialization and property access
   - Legal action generation
   - Action application and state transitions
   - Terminal state detection
   - Reward calculation
   - Serialization and deserialization

3. Integration
   - End-to-end testing of MCTS with real state implementations
   - Testing with various exploration weights and simulation counts
   - Handling of terminal states

## Adding New Tests

When adding new state implementations, follow this pattern:

1. Create a new test file in `tests/ai/mcts/states/` named `test_[entity]_state.py`
2. Implement test cases for all key methods: get_legal_actions, apply_action, is_terminal, get_reward
3. Test serialization and creation from entity methods
4. Add immutability tests to ensure actions don't modify the original state

## Benchmarking

For performance testing of MCTS, add the `--benchmark` flag:

```bash
python -m unittest tests/ai/mcts/test_integration.py --benchmark
```

This will run additional performance tests to measure MCTS execution time with various configurations.