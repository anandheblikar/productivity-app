import argparse
import json
from pathlib import Path


def load_tasks(path: Path) -> list[dict]:
    if not path.exists():
        return []

    tasks = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(tasks, list):
        raise ValueError(f"Expected a list of tasks in {path}")
    return tasks


def save_tasks(path: Path, tasks: list[dict]) -> None:
    path.write_text(json.dumps(tasks, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Keep track of a simple to-do list.")
    parser.add_argument(
        "--data-file",
        type=Path,
        default=Path(__file__).with_name("tasks.json"),
        help="where tasks are saved (default: tasks.json beside this script)",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    add_command = commands.add_parser("add", help="add a task")
    add_command.add_argument("title", nargs="+", help="what needs to be done")

    commands.add_parser("list", help="show all tasks")

    done_command = commands.add_parser("done", help="mark a task as complete")
    done_command.add_argument("task_id", type=int, help="the task number")

    args = parser.parse_args()
    try:
        tasks = load_tasks(args.data_file)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error(f"could not load tasks: {error}")

    if args.command == "add":
        task_id = max((task["id"] for task in tasks), default=0) + 1
        title = " ".join(args.title)
        tasks.append({"id": task_id, "title": title, "completed": False})
        save_tasks(args.data_file, tasks)
        print(f"Added task {task_id}: {title}")
    elif args.command == "list":
        if not tasks:
            print("Your to-do list is empty.")
            return

        for task in tasks:
            status = "x" if task["completed"] else " "
            print(f"{task['id']}. [{status}] {task['title']}")
    elif args.command == "done":
        task = next((task for task in tasks if task["id"] == args.task_id), None)
        if task is None:
            parser.error(f"task {args.task_id} was not found")
        task["completed"] = True
        save_tasks(args.data_file, tasks)
        print(f"Completed task {args.task_id}: {task['title']}")


if __name__ == "__main__":
    main()
