---
title: Python Tips
tags:
  - python
  - programming
date: 2026-06-28
---

# Python Tips & Tricks

## F-Strings (Python 3.6+)

```python
name = "World"
print(f"Hello, {name}!")
```

## List Comprehensions

```python
squares = [x**2 for x in range(10)]
evens = [x for x in range(20) if x % 2 == 0]
```

## Useful Libraries for ML

- NumPy - Numerical computing
- Pandas - Data manipulation
- Scikit-learn - Machine learning (see [[Machine Learning]])
- PyTorch / TensorFlow - Deep learning

## File I/O Patterns

```python
from pathlib import Path
content = Path("file.md").read_text()
```

See also: [[Home]] | [[Project Alpha]]