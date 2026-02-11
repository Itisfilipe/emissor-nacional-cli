from __future__ import annotations


def main() -> None:
    """Entry point for the Emissor Nacional TUI."""
    from emissor.tui.app import EmissorApp

    app = EmissorApp()
    app.run()


if __name__ == "__main__":
    main()
