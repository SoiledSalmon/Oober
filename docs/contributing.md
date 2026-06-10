# Contributing Standards: Oober (R5)

Welcome to Oober! This guide outlines the workflow and standards required to contribute to this repository. Please read this document before creating a pull request.

---

## 1. Local Development Setup

To set up a local development environment, follow these steps:

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/SoiledSalmon/Oober.git
   cd Oober
   ```

2. **Python Environment Setup**:
   Ensure you are using Python 3.10+ and set up a clean virtual environment:
   ```bash
   python -m venv .venv
   ```
   Activate the virtual environment depending on your shell:
   - *Windows PowerShell*: `.venv\Scripts\Activate.ps1`
   - *macOS/Linux*: `source .venv/bin/activate`

3. **Install Dependencies**:
   Install all dependencies, including testing utilities:
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify Environment**:
   Run the backend verification suite to verify that everything works correctly:
   ```bash
   python tests/verify_backend.py
   ```

---

## 2. Coding Standards

### Backend (Python)
- **Formatting**: Adhere to PEP 8 style standards. We suggest using `black` or `autopep8` for auto-formatting.
- **Typing**: Use static type hints for function signatures (`def func(param: type) -> return_type:`) to keep the code clear.
- **Naming**: Use `snake_case` for variables, functions, and modules, and `PascalCase` for classes.
- **Docstrings**: All public methods and modules must have descriptive docstrings explaining parameters, return values, and exceptions.

### Frontend (JavaScript, CSS, HTML)
- **Namespace isolation**: Do not pollute the global scope. Attach all modules and variables under the `window.OoberApp` namespace (e.g., `window.OoberApp.myModule = { ... }`).
- **Formatting**: Use standard 2-space indentation.
- **Strict Mode**: Wrap JavaScript files in an IIFE and enable `'use strict';`.
- **CSS Variable Design**: Use predefined custom properties (defined in `frontend/css/base.css`) for layout, spacing, colors, and shadows. Do not use ad-hoc inline styling.

---

## 3. Branching Strategy

We follow a structured branch naming convention:
- **`main`**: Production-ready branch. Do not commit directly to `main`.
- **`feature/feature-name`**: For new features or enhancements.
- **`bugfix/bug-description`**: For bug fixes.
- **`docs/doc-topic`**: For documentation updates.

All changes must go through a pull request into `main` and pass the verification suites.

---

## 4. Testing & Verification Expectations

Any changes to code logic must be validated against tests:
- **No Regression**: Run `python tests/verify_backend.py` before opening a pull request. Any failing test is a blocker.
- **New Coverage**: If you implement a new feature or optimization metric, you must provide corresponding unit tests in `tests/`.
- **Lint Check**: Ensure that no unused imports or variables are introduced.

---

## 5. Pull Request Process

1. **Format & Test**: Format your code and ensure all tests pass.
2. **Branch & Commit**: Commit changes with clear, descriptive commit messages.
3. **Open Pull Request**: Open a PR against `main`. Explain the changes, design decisions, and what was tested.
4. **Code Review**: At least one code maintainer must review and approve the changes before they can be merged.
