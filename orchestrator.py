from agents import InputAgent, FeatureExtractionAgent, DecisionAgent, ExecutionAgent, ReportAgent


class AudioCompressionOrchestrator:
    def __init__(self):
        self.input_agent = InputAgent()
        self.feature_agent = FeatureExtractionAgent()
        self.decision_agent = DecisionAgent()
        self.execution_agent = ExecutionAgent()
        self.report_agent = ReportAgent()

    def run_pipeline(self, filepath: str):
        metadata = self.input_agent.load_and_validate(filepath)
        if metadata is None:
            return {"error": "InputAgent failed"}

        features = self.feature_agent.extract(filepath)
        if features is None:
            return {"error": "FeatureExtractionAgent failed"}

        decision = self.decision_agent.decide(metadata, features)
        if decision is None:
            return {"error": "DecisionAgent failed"}

        execution = self.execution_agent.compress(
            filepath=filepath,
            codec=decision["codec"],
            bitrate_kbps=decision["bitrate"],
            sample_rate_hz=decision["sample_rate"],
            channels=decision["channels"],
        )
        if execution is None:
            return {"error": "ExecutionAgent failed"}

        report = self.report_agent.generate(
            original_filepath=filepath,
            compressed_filepath=execution["output_filepath"],
            compression_params={
                "codec": execution["codec"],
                "bitrate_kbps": execution["bitrate_kbps"],
                "sample_rate_hz": execution["sample_rate_hz"],
                "channels": execution["channels"],
                "decision_source": decision.get("decision_source", "fallback"),
                "reasoning": decision["reasoning"],
            },
        )
        if report is None:
            return {"error": "ReportAgent failed"}

        return {
            "metadata": metadata,
            "features": features,
            "decision": decision,
            "execution": execution,
            "report": report,
        }


if __name__ == "__main__":
    orchestrator = AudioCompressionOrchestrator()
    result = orchestrator.run_pipeline("C:\\Users\\lenovo\\Desktop\\audio-compression-project\\data\\audio_files\\test.wav")
    print(result)