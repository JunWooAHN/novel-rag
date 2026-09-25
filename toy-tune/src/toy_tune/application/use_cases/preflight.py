from toy_tune.application.ports.engines import EnvironmentInspector


def preflight(inspector: EnvironmentInspector, probe_gpu: bool = False) -> dict:
    return inspector.inspect(probe_gpu)
