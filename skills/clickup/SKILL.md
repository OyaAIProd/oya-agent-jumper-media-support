---
name: clickup
display_name: "ClickUp"
description: "Create comprehensive project plans in ClickUp — tasks, subtasks, checklists, dependencies, priorities, and time estimates"
category: productivity
icon: check-square
skill_type: sandbox
catalog_type: platform
requirements: "httpx>=0.25"
resource_requirements:
  - env_var: CLICKUP_ACCESS_TOKEN
    name: "ClickUp Access Token"
    description: "OAuth access token (auto-provided by gateway connection)"
  - env_var: CLICKUP_TEAM_ID
    name: "ClickUp Team ID"
    description: "Workspace (team) ID (auto-detected after OAuth connection)"
config_schema:
  properties:
    default_space_id:
      type: string
      label: "Default Space ID"
      description: "Skip space lookup by providing a default space ID"
      placeholder: "12345678"
      group: defaults
    default_list_id:
      type: string
      label: "Default List ID"
      description: "Skip list lookup by providing a default list ID"
      placeholder: "901234567"
      group: defaults
    default_priority:
      type: select
      label: "Default Priority"
      description: "Priority for new tasks when not specified"
      options: ["Urgent", "High", "Normal", "Low"]
      default: "Normal"
      group: defaults
    default_assignee:
      type: string
      label: "Default Assignee"
      description: "ClickUp user ID to assign tasks to by default"
      placeholder: "12345678"
      group: defaults
    task_rules:
      type: text
      label: "Task Rules"
      description: "Rules for how the LLM should create and organize tasks"
      placeholder: "- Break large deliverables into tasks of 1-8 hours\n- Always include a description with acceptance criteria\n- Use tags to categorize by workstream"
      group: rules
    priority_rules:
      type: text
      label: "Priority Rules"
      description: "Rules for how the LLM should determine task priority"
      placeholder: "- Blockers and critical path items → Urgent\n- Key deliverables → High\n- Standard work → Normal\n- Nice-to-haves → Low"
      group: rules
    checklist_rules:
      type: text
      label: "Checklist Rules"
      description: "Rules for when and how to add checklists to tasks"
      placeholder: "- Add a 'Definition of Done' checklist to every task\n- Include review and QA steps\n- Keep checklist items actionable and specific"
      group: rules
tool_schema:
  name: clickup
  description: "Create comprehensive project plans in ClickUp — manage spaces, lists, tasks, subtasks, checklists, and dependencies"
  parameters:
    type: object
    properties:
      action:
        type: "string"
        description: "Which operation to perform"
        enum: ['get_spaces', 'get_folders', 'get_lists', 'get_members', 'get_tasks', 'create_task', 'create_subtask', 'add_checklist', 'add_dependency', 'update_task', 'create_plan']
      space_id:
        type: "string"
        description: "Space ID — required for get_folders, get_lists (when listing by space)"
        default: ""
      folder_id:
        type: "string"
        description: "Folder ID — for get_lists (when listing by folder)"
        default: ""
      list_id:
        type: "string"
        description: "List ID — required for get_tasks, create_task, create_subtask, create_plan"
        default: ""
      task_id:
        type: "string"
        description: "Task ID — required for add_checklist, add_dependency, update_task"
        default: ""
      parent_task_id:
        type: "string"
        description: "Parent task ID — required for create_subtask"
        default: ""
      name:
        type: "string"
        description: "Task or subtask name"
        default: ""
      description:
        type: "string"
        description: "Task description (markdown supported)"
        default: ""
      status:
        type: "string"
        description: "Task status for update_task (must match list workflow)"
        default: ""
      priority:
        type: "integer"
        description: "Priority: 1=Urgent, 2=High, 3=Normal, 4=Low"
        default: 0
      due_date:
        type: "string"
        description: "Due date — ISO 8601 string (e.g. 2025-03-15) or unix ms"
        default: ""
      time_estimate_hours:
        type: "number"
        description: "Time estimate in hours (converted to milliseconds for ClickUp)"
        default: 0
      assignee:
        type: "string"
        description: "ClickUp user ID to assign the task to"
        default: ""
      tags:
        type: "string"
        description: "Comma-separated tags (e.g. 'planning,phase-1')"
        default: ""
      depends_on:
        type: "string"
        description: "Task ID that this task depends on — for add_dependency"
        default: ""
      checklist_name:
        type: "string"
        description: "Checklist name — for add_checklist"
        default: ""
      checklist_items:
        type: "string"
        description: "Newline-separated checklist items — for add_checklist"
        default: ""
      plan:
        type: "string"
        description: "JSON array of task objects for create_plan — each object can have: name, description, priority (1-4), time_estimate_hours, tags (comma-separated), assignee, due_date, subtasks (array of {name, description, time_estimate_hours, assignee}), checklist ({name, items: [string]}), depends_on_index (0-based index of another task in this plan)"
        default: ""
    required: [action]
---
# ClickUp

Create and manage comprehensive project plans in ClickUp. Supports the full hierarchy: Workspace > Space > Folder > List > Task > Subtask > Checklist.

## Navigation
- **get_spaces** — List all spaces in the workspace.
- **get_folders** — List folders in a space. Provide `space_id`.
- **get_lists** — List lists in a space or folder. Provide `space_id` or `folder_id`.
- **get_members** — Get workspace members for assigning tasks.
- **get_tasks** — List tasks in a list. Provide `list_id`.

## Task Management
- **create_task** — Create a task. Provide `list_id`, `name`, and optional `description`, `priority`, `due_date`, `time_estimate_hours`, `assignee`, `tags`.
- **create_subtask** — Create a subtask. Provide `list_id`, `parent_task_id`, `name`, and optional fields.
- **add_checklist** — Add a checklist to a task. Provide `task_id`, `checklist_name`, `checklist_items` (newline-separated).
- **add_dependency** — Set a dependency. Provide `task_id` and `depends_on` (the task ID it depends on).
- **update_task** — Update task fields. Provide `task_id` and fields to change.

## Batch Plan Creation
- **create_plan** — Create a full project plan in one action. Provide `list_id` and `plan` as a JSON array of task objects. Each task can include subtasks, checklists, and dependencies (via `depends_on_index` referencing other tasks in the plan by array position).

### Example plan JSON:
```json
[
  {
    "name": "Define project scope",
    "description": "Document goals, deliverables, constraints",
    "priority": 2,
    "time_estimate_hours": 4,
    "tags": "planning",
    "subtasks": [
      {"name": "Identify stakeholders", "time_estimate_hours": 1},
      {"name": "Define success criteria", "time_estimate_hours": 2}
    ],
    "checklist": {
      "name": "Scope checklist",
      "items": ["Goals documented", "Budget confirmed", "Timeline agreed"]
    }
  },
  {
    "name": "Technical design",
    "description": "Architecture and design docs",
    "priority": 2,
    "time_estimate_hours": 8,
    "depends_on_index": 0
  }
]
```

### Priority values: 1=Urgent, 2=High, 3=Normal, 4=Low
