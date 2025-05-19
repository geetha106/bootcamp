import json
import csv
import io
import time
from typing import List, Dict, Any
from datetime import datetime
from config.config import get_config


class ResultFormatter:
    """Handles formatting of paper processing results into different output formats."""

    def __init__(self):
        self.config = get_config()

    def format_json(self, results: List[Dict[str, Any]], processing_time: float) -> str:
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
        
        if not self.config.output.include_summary:
            output.pop("summary")

        return json.dumps(output, indent=2 if self.config.output.pretty_print_json else None)

    def format_csv(self, results: List[Dict[str, Any]], processing_time: float) -> str:
        """Format results as a CSV string with Excel-friendly formatting."""
        output = io.StringIO()
        writer = csv.writer(output, delimiter=self.config.output.csv_delimiter)

        # Write header with separate columns for entity information
        header = [
            "Paper ID", "Source", "Status", "Title", "Abstract",
            "Figure ID", "Caption", "Figure URL"
        ]

        # Add entity columns based on configuration
        max_entities = self.config.output.max_entities_in_csv
        for i in range(1, max_entities + 1):
            header.extend([f"Entity {i}", f"Entity {i} Type"])

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
                    *["" for _ in range(max_entities * 2)]  # Empty entity columns
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

                    # Add entity information (up to max_entities)
                    entities = figure.get("entities", [])
                    for i in range(max_entities):
                        if i < len(entities):
                            entity = entities[i]
                            row_data.extend([
                                entity.get("entity", ""),
                                entity.get("type", "")
                            ])
                        else:
                            row_data.extend(["", ""])  # Empty entity slot

                    writer.writerow(row_data)

        # Write summary if enabled
        if self.config.output.include_summary:
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
        self.config = get_config()

    def start_timing(self):
        """Start timing the batch processing."""
        self.start_time = time.time()

    def format_results(self, results: List[Dict[str, Any]], format_type: str = "json") -> str:
        """Format results in the specified format."""
        if not self.start_time:
            raise ValueError("Timer not started. Call start_timing() before processing.")

        processing_time = time.time() - self.start_time

        format_type = format_type.lower()
        if format_type not in self.config.output.formats:
            raise ValueError(f"Unsupported format type: {format_type}. Allowed formats: {self.config.output.formats}")

        if format_type == "json":
            return self.formatter.format_json(results, processing_time)
        elif format_type == "csv":
            return self.formatter.format_csv(results, processing_time)
        else:
            raise ValueError(f"Unsupported format type: {format_type}") 