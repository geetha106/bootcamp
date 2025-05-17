import json
import csv
import io
import time
from typing import List, Dict, Any
from datetime import datetime


class ResultFormatter:
    """Handles formatting of paper processing results into different output formats."""

    @staticmethod
    def format_json(results: List[Dict[str, Any]], processing_time: float) -> str:
        """Format results as a JSON string."""
        output = {
            "results": results,
            "summary": {
                "total_requested": len(results),
                "successful": sum(1 for r in results if r.get("status") == "success"),
                "failed": sum(1 for r in results if r.get("status") == "error"),
                "processing_time": round(processing_time, 2)
            }
        }
        return json.dumps(output, indent=2)

    @staticmethod
    def format_csv(results: List[Dict[str, Any]], processing_time: float) -> str:
        """Format results as a CSV string with Excel-friendly formatting."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header with separate columns for entity information
        header = [
            "Paper ID", "Source", "Status", "Title", "Abstract",
            "Figure ID", "Caption", "Figure URL",
            "Entity 1", "Entity 1 Type",
            "Entity 2", "Entity 2 Type",
            "Entity 3", "Entity 3 Type",
            "Entity 4", "Entity 4 Type",
            "Entity 5", "Entity 5 Type"
        ]
        writer.writerow(header)

        # Write data
        for result in results:
            if not result.get("figures"):
                # Write paper with no figures
                writer.writerow([
                    result.get("paper_id", ""),
                    result.get("source", ""),
                    result.get("status", ""),
                    result.get("title", ""),
                    result.get("abstract", ""),
                    "", "", "",  # Figure ID, Caption, URL
                    *["" for _ in range(10)]  # Empty entity columns (5 entities * 2 fields)
                ])
            else:
                # Write each figure as a separate row
                for figure in result["figures"]:
                    # Prepare base row data
                    row_data = [
                        result.get("paper_id", ""),
                        result.get("source", ""),
                        result.get("status", ""),
                        result.get("title", ""),
                        result.get("abstract", ""),
                        figure.get("figure_id", ""),
                        figure.get("caption", ""),
                        figure.get("figure_url", "")
                    ]

                    # Add entity information (up to 5 entities)
                    entities = figure.get("entities", [])
                    for i in range(5):  # Handle up to 5 entities
                        if i < len(entities):
                            entity = entities[i]
                            row_data.extend([
                                entity.get("entity", ""),
                                entity.get("type", "")
                            ])
                        else:
                            row_data.extend(["", ""])  # Empty entity slot

                    writer.writerow(row_data)

        # Write summary as a separate section with blank rows for clarity
        writer.writerow([])
        writer.writerow([])
        writer.writerow(["Processing Summary"])
        writer.writerow(["Total Papers Requested", len(results)])
        writer.writerow(["Successfully Processed", sum(1 for r in results if r.get("status") == "success")])
        writer.writerow(["Failed to Process", sum(1 for r in results if r.get("status") == "error")])
        writer.writerow(["Total Processing Time (seconds)", round(processing_time, 2)])

        return output.getvalue()


class BatchResultExporter:
    """Handles exporting batch processing results in different formats."""

    def __init__(self):
        self.formatter = ResultFormatter()
        self.start_time = None

    def start_timing(self):
        """Start timing the batch processing."""
        self.start_time = time.time()

    def format_results(self, results: List[Dict[str, Any]], format_type: str = "json") -> str:
        """Format results in the specified format."""
        if not self.start_time:
            raise ValueError("Timer not started. Call start_timing() before processing.")

        processing_time = time.time() - self.start_time

        if format_type.lower() == "json":
            return self.formatter.format_json(results, processing_time)
        elif format_type.lower() == "csv":
            return self.formatter.format_csv(results, processing_time)
        else:
            raise ValueError(f"Unsupported format type: {format_type}") 