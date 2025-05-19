import sys
import os

# Add the project root to the path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cli.cli import ingest, export
import typer

app = typer.Typer()


@app.command()
def test_export():
    """
    Test the export functionality with a sample paper
    """
    # First ingest a paper if needed
    pmc_id = "PMC3539452"  # Use a known PMC ID

    # Ingest the paper
    try:
        ingest(pmc_id)
        print(f"Successfully ingested paper {pmc_id}")
    except Exception as e:
        print(f"Error ingesting paper: {e}")
        return

    # Now export it in JSON format
    print("\nExporting as JSON:")
    export(pmc_id, "json")

    # And in CSV format
    print("\nExporting as CSV:")
    export(pmc_id, "csv")


if __name__ == "__main__":
    app()