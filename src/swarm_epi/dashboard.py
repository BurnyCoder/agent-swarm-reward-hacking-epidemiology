"""Live metrics dashboard via trackio (Hugging Face, local-first, wandb-compatible API; https://huggingface.co/docs/trackio).

Local context: one trackio run per swarm replicate (`group` = condition) logs per-round prevalence, flag rate, mean
belief-probe P(Yes), and throughput; `trackio show --project swarm-epi` opens the local Gradio dashboard while runs
are in progress. Failures here are logged and swallowed so monitoring can never crash an experiment.
Global context: called from `swarm.py` once per round.
"""

from __future__ import annotations  # forward references

import logging  # warnings on dashboard errors

log = logging.getLogger("swarm_epi.dashboard")  # module logger
PROJECT = "swarm-epi"  # trackio project name


class Dashboard:
    """Best-effort wrapper around a trackio Run."""

    def __init__(self, run_id: str, group: str, config: dict, enabled: bool = True):
        self.run = None  # trackio Run or None when disabled/failed
        if not enabled:
            return
        try:
            import trackio  # imported lazily so tests do not need the dashboard stack

            self.run = trackio.init(project=PROJECT, name=run_id, group=group, config=config, resume="allow",
                                    auto_log_gpu=True)  # GPU utilisation/memory alongside experiment metrics
        except Exception as e:  # noqa: BLE001 - dashboard must never break a run
            log.warning("trackio init failed: %s", e)

    def log(self, metrics: dict, step: int) -> None:
        """Log one round of metrics."""
        if self.run is None:
            return
        try:
            self.run.log(metrics, step=step)  # trackio.Run.log(metrics, step)
        except Exception as e:  # noqa: BLE001
            log.warning("trackio log failed: %s", e)

    def finish(self) -> None:
        """Close the run."""
        if self.run is not None:
            try:
                self.run.finish()
            except Exception as e:  # noqa: BLE001
                log.warning("trackio finish failed: %s", e)
