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
        cnr_token=None,
        organization=None,
        overwrite_from_index=False,
        overwrite_from_index_token=None,
        state_seq=("in_progress", "finished"),
        op_type="add",
        deprecation_list=None,
    ):
        tid = self._gen_task_id()
        self.task_state_seq[tid] = list(state_seq)
        self.tasks[tid] = {
            "id": tid,
            "state": self.task_state_seq[tid].pop(0),
            "state_reason": "state_reason",
            "state_history": [],
            "from_index": index,
            "bundles": map_or_op,
            "from_index_resolved": index + "-resolved",
            "binary_image": binary_image,
            "binary_image_resolved": binary_image + "-resolved",
            "bundle_mapping": {},
            "index_image": "feed.com/index/image:tag",
            "arches": arches,
            "batch": 123,
            "updated": "2020-05-26T19:33:58.759687Z",
            "user": "tbrady@DOMAIN.LOCAL",
            "removed_operators": ["operator-%s" % k for k in map_or_op],
            "organization": None,
            "omps_operator_version": {},
            "distribution_scope": "",
            "deprecation_list": [] if not deprecation_list else deprecation_list,
        }

        if op_type == "rm":
            self.tasks[tid]["request_type"] = "rm"
        if op_type == "add":
            self.tasks[tid]["request_type"] = "add"
            self.tasks[tid]["bundle_mapping"] = {"operator-1": map_or_op}

        return self.tasks[tid]

    def get_task(self, tid):
        task = self.tasks[tid]
        state = self.task_state_seq[tid].pop(0)
        task["state"] = state
        return task


class FakeCollector(object):
    """Fake backend for PushCollector.
    Tests can access the attributes on this collector to see
    which push items & files were created during a task.
    """

    def __init__(self):
        self.items = []
        self.file_content = {}

    def update_push_items(self, items):
        self.items.extend(items)

    def attach_file(self, filename, content):
        self.file_content[filename] = content

    def append_file(self, filename, content):
        self.file_content[filename] = self.file_content.get(filename, b"") + content
