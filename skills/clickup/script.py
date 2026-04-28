import os
import json
import time
from datetime import datetime
import httpx

BASE = "https://api.clickup.com/api/v2"
DELAY = 0.1


def api_get(token, path, timeout=15):
    """GET request to ClickUp API with rate-limit delay."""
    time.sleep(DELAY)
    with httpx.Client(timeout=timeout) as c:
        r = c.get(f"{BASE}/{path}", headers={"Authorization": token})
        r.raise_for_status()
        return r.json()


def api_post(token, path, body, timeout=15):
    """POST request to ClickUp API with rate-limit delay."""
    time.sleep(DELAY)
    with httpx.Client(timeout=timeout) as c:
        r = c.post(
            f"{BASE}/{path}",
            headers={"Authorization": token, "Content-Type": "application/json"},
            json=body,
        )
        r.raise_for_status()
        return r.json()


def api_put(token, path, body, timeout=15):
    """PUT request to ClickUp API with rate-limit delay."""
    time.sleep(DELAY)
    with httpx.Client(timeout=timeout) as c:
        r = c.put(
            f"{BASE}/{path}",
            headers={"Authorization": token, "Content-Type": "application/json"},
            json=body,
        )
        r.raise_for_status()
        return r.json()


def parse_due_date(val):
    """Convert ISO 8601 date string or unix ms to int milliseconds."""
    if not val:
        return None
    if isinstance(val, (int, float)):
        return int(val)
    try:
        return int(val)
    except ValueError:
        pass
    try:
        dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)
    except (ValueError, AttributeError):
        return None


def build_task_body(inp):
    """Build task field dict from input params."""
    body = {}
    if inp.get("name"):
        body["name"] = inp["name"]
    if inp.get("description"):
        body["markdown_description"] = inp["description"]
    priority = inp.get("priority")
    if priority and int(priority) > 0:
        body["priority"] = int(priority)
    due = parse_due_date(inp.get("due_date"))
    if due:
        body["due_date"] = due
        body["due_date_time"] = False
    hours = inp.get("time_estimate_hours")
    if hours and float(hours) > 0:
        body["time_estimate"] = int(float(hours) * 3600000)
    assignee = inp.get("assignee")
    if assignee:
        body["assignees"] = [int(assignee)]
    tags_str = inp.get("tags", "")
    if tags_str:
        body["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]
    return body


# --- Actions ---


def do_get_spaces(token, team_id):
    data = api_get(token, f"team/{team_id}/space?archived=false")
    spaces = data.get("spaces", [])
    return {
        "spaces": [
            {"id": s["id"], "name": s["name"]}
            for s in spaces
        ],
        "count": len(spaces),
    }


def do_get_folders(token, space_id):
    data = api_get(token, f"space/{space_id}/folder?archived=false")
    folders = data.get("folders", [])
    return {
        "folders": [
            {"id": f["id"], "name": f["name"]}
            for f in folders
        ],
        "count": len(folders),
    }


def do_get_lists(token, space_id=None, folder_id=None):
    if folder_id:
        data = api_get(token, f"folder/{folder_id}/list?archived=false")
    elif space_id:
        data = api_get(token, f"space/{space_id}/list?archived=false")
    else:
        return {"error": "Provide space_id or folder_id"}
    lists = data.get("lists", [])
    return {
        "lists": [
            {"id": l["id"], "name": l["name"], "task_count": l.get("task_count")}
            for l in lists
        ],
        "count": len(lists),
    }


def do_get_members(token, team_id):
    data = api_get(token, f"team/{team_id}")
    members = data.get("team", {}).get("members", [])
    return {
        "members": [
            {
                "id": m.get("user", {}).get("id"),
                "username": m.get("user", {}).get("username"),
                "email": m.get("user", {}).get("email"),
            }
            for m in members
        ],
        "count": len(members),
    }


def do_get_tasks(token, list_id):
    data = api_get(token, f"list/{list_id}/task?archived=false&include_closed=false")
    tasks = data.get("tasks", [])
    return {
        "tasks": [
            {
                "id": t["id"],
                "name": t["name"],
                "status": t.get("status", {}).get("status"),
                "priority": t.get("priority", {}).get("priority") if t.get("priority") else None,
                "url": t.get("url", f"https://app.clickup.com/t/{t['id']}"),
            }
            for t in tasks
        ],
        "count": len(tasks),
    }


def do_create_task(token, list_id, inp):
    body = build_task_body(inp)
    data = api_post(token, f"list/{list_id}/task", body)
    return {
        "id": data["id"],
        "name": data.get("name", ""),
        "url": data.get("url", f"https://app.clickup.com/t/{data['id']}"),
    }


def do_create_subtask(token, list_id, parent_task_id, inp):
    body = build_task_body(inp)
    body["parent"] = parent_task_id
    data = api_post(token, f"list/{list_id}/task", body)
    return {
        "id": data["id"],
        "name": data.get("name", ""),
        "url": data.get("url", f"https://app.clickup.com/t/{data['id']}"),
    }


def do_add_checklist(token, task_id, checklist_name, items_str):
    cl_data = api_post(token, f"task/{task_id}/checklist", {"name": checklist_name})
    checklist_id = cl_data.get("checklist", {}).get("id")
    if not checklist_id:
        return {"error": "Failed to create checklist"}
    items = [i.strip() for i in items_str.split("\n") if i.strip()]
    for item in items:
        api_post(token, f"checklist/{checklist_id}/checklist_item", {"name": item})
    return {"checklist_id": checklist_id, "items_added": len(items)}


def do_add_dependency(token, task_id, depends_on):
    api_post(token, f"task/{task_id}/dependency", {
        "depends_on": depends_on,
    })
    return {"ok": True, "task_id": task_id, "depends_on": depends_on}


def do_update_task(token, task_id, inp):
    body = build_task_body(inp)
    if inp.get("status"):
        body["status"] = inp["status"]
    data = api_put(token, f"task/{task_id}", body)
    return {
        "id": data["id"],
        "name": data.get("name", ""),
        "url": data.get("url", f"https://app.clickup.com/t/{data['id']}"),
    }


def do_create_plan(token, list_id, plan_json):
    """Batch-create a full project plan: tasks, subtasks, checklists, dependencies."""
    if isinstance(plan_json, str):
        plan = json.loads(plan_json)
    else:
        plan = plan_json

    index_to_task_id = {}
    results = []
    errors = []
    subtasks_created = 0
    checklists_created = 0
    dependencies_created = 0

    # Pass 1: Create all top-level tasks
    for idx, task_def in enumerate(plan):
        try:
            task_result = do_create_task(token, list_id, task_def)
            index_to_task_id[idx] = task_result["id"]
            results.append({
                "index": idx,
                "id": task_result["id"],
                "name": task_def.get("name", ""),
                "url": task_result["url"],
                "subtasks": [],
                "checklist": None,
            })
        except Exception as e:
            errors.append({"index": idx, "name": task_def.get("name", ""), "error": str(e)})
            results.append({"index": idx, "name": task_def.get("name", ""), "error": str(e)})

    # Pass 2: Create subtasks
    for idx, task_def in enumerate(plan):
        parent_id = index_to_task_id.get(idx)
        if not parent_id:
            continue
        for sub_def in task_def.get("subtasks", []):
            try:
                sub_result = do_create_subtask(token, list_id, parent_id, sub_def)
                results[idx]["subtasks"].append({
                    "id": sub_result["id"],
                    "name": sub_def.get("name", ""),
                    "url": sub_result["url"],
                })
                subtasks_created += 1
            except Exception as e:
                errors.append({
                    "parent_index": idx,
                    "subtask": sub_def.get("name", ""),
                    "error": str(e),
                })

    # Pass 3: Create checklists
    for idx, task_def in enumerate(plan):
        task_id = index_to_task_id.get(idx)
        if not task_id:
            continue
        cl = task_def.get("checklist")
        if not cl:
            continue
        try:
            cl_name = cl.get("name", "Checklist")
            cl_items = "\n".join(cl.get("items", []))
            cl_result = do_add_checklist(token, task_id, cl_name, cl_items)
            results[idx]["checklist"] = cl_result
            checklists_created += 1
        except Exception as e:
            errors.append({
                "index": idx,
                "checklist": cl.get("name", ""),
                "error": str(e),
            })

    # Pass 4: Create dependencies
    for idx, task_def in enumerate(plan):
        task_id = index_to_task_id.get(idx)
        if not task_id:
            continue
        dep_idx = task_def.get("depends_on_index")
        if dep_idx is None:
            continue
        dep_task_id = index_to_task_id.get(dep_idx)
        if not dep_task_id:
            errors.append({
                "index": idx,
                "error": f"depends_on_index {dep_idx} not found in created tasks",
            })
            continue
        try:
            do_add_dependency(token, task_id, dep_task_id)
            dependencies_created += 1
        except Exception as e:
            errors.append({
                "index": idx,
                "dependency_on": dep_idx,
                "error": str(e),
            })

    return {
        "tasks_created": len(index_to_task_id),
        "subtasks_created": subtasks_created,
        "checklists_created": checklists_created,
        "dependencies_created": dependencies_created,
        "tasks": results,
        "errors": errors,
    }


# --- Main ---

try:
    token = os.environ["CLICKUP_ACCESS_TOKEN"]
    team_id = os.environ["CLICKUP_TEAM_ID"]
    inp = json.loads(os.environ.get("INPUT_JSON", "{}"))
    action = inp.get("action", "")

    if action == "get_spaces":
        result = do_get_spaces(token, team_id)
    elif action == "get_folders":
        result = do_get_folders(token, inp.get("space_id", ""))
    elif action == "get_lists":
        result = do_get_lists(token, space_id=inp.get("space_id"), folder_id=inp.get("folder_id"))
    elif action == "get_members":
        result = do_get_members(token, team_id)
    elif action == "get_tasks":
        result = do_get_tasks(token, inp.get("list_id", ""))
    elif action == "create_task":
        result = do_create_task(token, inp.get("list_id", ""), inp)
    elif action == "create_subtask":
        result = do_create_subtask(token, inp.get("list_id", ""), inp.get("parent_task_id", ""), inp)
    elif action == "add_checklist":
        result = do_add_checklist(token, inp.get("task_id", ""), inp.get("checklist_name", "Checklist"), inp.get("checklist_items", ""))
    elif action == "add_dependency":
        result = do_add_dependency(token, inp.get("task_id", ""), inp.get("depends_on", ""))
    elif action == "update_task":
        result = do_update_task(token, inp.get("task_id", ""), inp)
    elif action == "create_plan":
        result = do_create_plan(token, inp.get("list_id", ""), inp.get("plan", "[]"))
    else:
        result = {"error": f"Unknown action: {action}"}

    print(json.dumps(result))

except Exception as e:
    print(json.dumps({"error": str(e)}))
