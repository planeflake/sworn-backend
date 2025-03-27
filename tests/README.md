# Sworn Backend Tests

This directory contains tests for the Sworn Backend application.

## Structure

- `/ai/mcts` - Tests for Monte Carlo Tree Search implementation and state classes
  - `/ai/mcts/states` - Tests for specific entity state implementations
- `/game_state` - Tests for game state entities and services

## Running Tests

### MCTS Tests

To run all MCTS tests:

```bash
# Run all MCTS tests
python tests/ai/mcts/run_tests.py --all

# Run only core MCTS implementation tests
python tests/ai/mcts/run_tests.py --core

# Run only state implementation tests
python tests/ai/mcts/run_tests.py --states

# Run only integration tests
python tests/ai/mcts/run_tests.py --integration

# Run specific state tests
python tests/ai/mcts/run_tests.py --trader
python tests/ai/mcts/run_tests.py --player
python tests/ai/mcts/run_tests.py --equipment

# Enable benchmark timing
python tests/ai/mcts/run_tests.py --all --benchmark
```

### Other Tests

```bash
# Run specific test modules
python -m unittest tests.game_state.entities.test_equipment
python -m unittest tests.game_state.services.test_item_service
```

## Writing Tests

When writing new tests:

1. Place tests in the appropriate subdirectory matching the structure of the main application
2. Use descriptive test method names that clearly explain what's being tested
3. Follow the naming convention: `test_*.py` for test files
4. For MCTS state tests, follow the pattern in `tests/ai/mcts/states/`

## Test Structure

Each test class should test a single class or functionality. Tests should be:

1. Independent - tests should not rely on the state from other tests
2. Focused - each test method should test one specific behavior
3. Complete - test normal operation, edge cases, and error conditions

For MCTS state classes in particular, make sure to test:
- State initialization
- Action generation with `get_legal_actions()`
- Action application with `apply_action()`
- Terminal state detection with `is_terminal()`
- Reward calculation with `get_reward()`
- Serialization and deserialization with `to_dict()` and `from_dict()`