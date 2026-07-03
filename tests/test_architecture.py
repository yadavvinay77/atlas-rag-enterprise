from enterprise_rag.architecture import architecture_report


def test_architecture_report_lists_requested_layers() -> None:
    report = architecture_report()
    layers = {layer.layer for layer in report.layers}

    assert "3. Chunking" in layers
    assert "6. Retrieval" in layers
    assert "7. Reranking" in layers
    assert "11. Evaluation" in layers
