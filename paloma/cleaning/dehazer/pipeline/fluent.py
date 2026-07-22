"""Fluent, method-chaining facade over the dehazing stage chain."""

from ..workflow import (
    Chain,
    EstimateAirlight,
    MoveCubeToDevice,
    RecoverAndSave,
    SmoothAirlight,
    Transmission,
    WorkflowContext,
)


class DehazePipeline:
    """Fluent, method-chaining facade over the (spatio-temporal) stage chain.

    Each method runs one stage against a shared
    :class:`~tess_dehazing.workflow.WorkflowContext` and returns ``self`` so a
    batch can be dehazed in a single expression::

        (DehazePipeline(cfg, use_gpu, batch_label)
            .load(cube, metadata)      # bind batch, move to device
            .estimate_airlight()       # Step 1
            .smooth_airlight()         # Step 2
            .transmission()            # Step 3
            .recover_and_save(output_dir))  # Step 4
        # equivalently: .load(cube, metadata).run(output_dir)

    Ordering is enforced by the underlying stages, which raise if called out of
    order.
    """

    def __init__(self, cfg, use_gpu=False, batch_label=""):
        self.ctx = WorkflowContext(cfg=cfg, use_gpu=use_gpu, label=batch_label)

    def load(self, cube, metadata):
        self.ctx.cube = cube
        self.ctx.metadata = metadata
        MoveCubeToDevice().run(self.ctx)
        return self

    def estimate_airlight(self):
        EstimateAirlight().run(self.ctx)
        return self

    def smooth_airlight(self):
        SmoothAirlight().run(self.ctx)
        return self

    def transmission(self):
        Transmission().run(self.ctx)
        return self

    def recover_and_save(self, output_dir):
        self.ctx.output_dir = output_dir
        RecoverAndSave().run(self.ctx)
        return self

    def run(self, output_dir):
        """Run Steps 1-4 in order on the already-loaded batch."""
        self.ctx.output_dir = output_dir
        chain = Chain([EstimateAirlight(), SmoothAirlight(),
                       Transmission(), RecoverAndSave()])
        chain.run(self.ctx)
        return self
