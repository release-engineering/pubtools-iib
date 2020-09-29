class FakeTaskManager(object):
    def __init__(self):
        self.tasks = {}
        self.task_id = 0
        self.task_state_seq = {}

    def _gen_task_id(self):
        ret = "task-%d" % self.task_id
        self.task_id += 1
        return ret

    def setup_task(
        self,
        index,
        map_or_op,
        arches,
        binary_image="binary-image",
        state_seq=("in_progress", "finished"),
        op_type="add",
    ):
        tid = self._gen_task_id()
        self.task_state_seq[tid] = list(state_seq)
        self.tasks[tid] = {
            "id": tid,
            "state": self.task_state_seq[tid].pop(0),
            "state_reason": "state_reason",
            "state_history": [],
            "from_index": index,
            "from_index_resolved": index + "-resolved",
            "bundles": map_or_op,
            "binary_image": binary_image,
            "binary_image_resolved": binary_image + "-resolved",
            "index_image": "index_image",
            "arches": arches,
        }
        import sys

        print >>sys.sderr, "OP_TYPE %s" % op_type

        if op_type == "remove":
            self.tasks[tid]["request_type"] = 2
            self.tasks[tid]["removed_operators"] = [
                "operator-%s" % k for k in map_or_op
            ]
        if op_type == "add":
            self.tasks[tid]["request_type"] = 1
            self.tasks[tid]["bundle_mapping"] = {"operator-1": map_or_op}

        return self.tasks[tid]

    def get_task(self, tid):
        task = self.tasks[tid]
        state = self.task_state_seq[tid].pop(0)
        task["state"] = state
        return task
