# Contributing to ADB Helper

Thank you for your interest in contributing to ADB Helper! We welcome contributions from the community and are grateful for any help you can provide.

## Before You Start

### 1. Fork the Repository
Please fork the repository to your own GitHub account before making any changes. This allows you to work on your features or fixes without affecting the main repository.

### 2. Start a Discussion
**Important**: Before creating a pull request, please open a thread in the [Discussions](https://github.com/mattintech/adbhelper/discussions) section to:
- Discuss your proposed changes
- Get feedback on your approach
- Ensure your contribution aligns with the project's goals
- Avoid duplicate work

This helps maintain code quality and ensures that your time is well spent on changes that will be accepted.

## Getting Started

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/mattintech/adbhelper.git
   cd adbhelper
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in development mode**
   ```bash
   pip install -e .
   pip install -r requirements.txt
   ```

4. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

## Contribution Guidelines

### Code Style

- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Add type hints where appropriate
- Keep line length under 100 characters when possible
- Use docstrings for all functions and classes

### Testing

- Test your changes with multiple Android devices if possible
- Ensure existing functionality still works
- Test on different platforms (macOS, Linux, Windows) if your change is platform-specific
- Include steps to reproduce any bugs you're fixing

### Commit Messages

Write clear and descriptive commit messages:
- Use present tense ("Add feature" not "Added feature")
- Keep the first line under 50 characters
- Provide detailed description after a blank line if needed
- Reference issue numbers when applicable

Example:
```
Add multi-device log filtering support

- Implement filtering across multiple device streams
- Add color coding for better device identification
- Fix UTF-8 encoding issues in log output

Fixes #123
```

### Pull Request Process

1. **Ensure your fork is up to date**
   ```bash
   git remote add upstream https://github.com/mattintech/adbhelper.git
   git fetch upstream
   git checkout develop
   git merge upstream/develop
   ```

2. **Make your changes**
   - Write clean, well-documented code
   - Follow the existing code structure and patterns
   - Update documentation if needed

3. **Test thoroughly**
   - Run the tool with various commands
   - Test edge cases
   - Verify no existing functionality is broken

4. **Update documentation**
   - Update README.md if you're adding new features
   - Add docstrings to new functions
   - Update help text in CLI commands

5. **Submit your pull request**
   - Push your branch to your fork
   - Create a pull request against the `develop` branch
   - Fill out the PR template completely
   - Reference the discussion thread where you proposed the change

## What We're Looking For

### Good First Issues

Look for issues labeled `good first issue` if you're new to the project. These are typically:
- Documentation improvements
- Simple bug fixes
- Small feature additions
- Code cleanup tasks

### Areas of Interest

We're particularly interested in contributions that:
- Improve cross-platform compatibility
- Add useful device management features
- Enhance the user experience
- Improve performance for multi-device operations
- Add better error handling and user feedback
- Extend wireless ADB capabilities

### What to Avoid

- Breaking changes to existing commands without discussion
- Large refactors without prior approval
- Adding heavy dependencies
- Platform-specific features that can't be reasonably supported across all platforms

## Code Review Process

1. All submissions require review before merging
2. We may suggest changes or improvements
3. Be responsive to feedback and questions
4. Once approved, we'll merge your contribution

## Development Tips

### Project Structure
```
adbhelper/
├── cli.py              # Main CLI entry point
├── commands/           # Command implementations
├── core/              # Core functionality
├── features/          # Additional features
└── utils/             # Utility functions
```

### Adding New Commands

1. Create a new file in `commands/` if needed
2. Implement your command using Click decorators
3. Register it in `commands/register.py`
4. Update help text and documentation

Example:
```python
@click.command()
@click.option('--option', help='Description')
@click.pass_context
def my_command(ctx, option):
    """Brief description of what this command does"""
    device_manager = ctx.obj['device_manager']
    # Implementation here
```

### Working with Rich Console

Use Rich for formatted output:
```python
from rich.console import Console
console = Console()

console.print("[green]Success message[/green]")
console.print("[yellow]Warning message[/yellow]")
console.print("[red]Error message[/red]")
```

## Questions?

If you have questions about contributing, please:
1. Check existing discussions and issues
2. Open a new discussion thread
3. Be patient - maintainers review contributions in their free time

## License

By contributing to ADB Helper, you agree that your contributions will be licensed under the MIT License.

## Thank You!

Thank you for contributing to ADB Helper! Your efforts help make Android device management easier for developers everywhere.