"""
Routes for the Agent Service.

This module defines the API routes for the Agent service. While there are multiple endpoints provided by the service,
the ones that require special attention due to their complexity are:

1. `execute_agent_task_step`:
   This route is significant because this is where the agent actually performs the work. The function handles
   executing the next step for a task based on its current state, and it requires careful implementation to ensure
   all scenarios (like the presence or absence of steps or a step marked as `last_step`) are handled correctly.

2. `upload_agent_task_artifacts`:
   This route allows for the upload of artifacts, supporting various URI types (e.g., s3, gcs, ftp, http).
   The support for different URI types makes it a bit more complex, and it's important to ensure that all
   supported URI types are correctly managed. NOTE: The Auto-GPT team will eventually handle the most common
   uri types for you.

3. `create_agent_task`:
   While this is a simpler route, it plays a crucial role in the workflow, as it's responsible for the creation
   of a new task.

Developers and contributors should be especially careful when making modifications to these routes to ensure
consistency and correctness in the system's behavior.
"""
import json
from typing import Optional

from fastapi import APIRouter, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse

from autogpt.errors import *
from autogpt.forge_log import CustomLogger
from autogpt.schema import *
from autogpt.tracing import tracing

base_router = APIRouter()

LOG = CustomLogger(__name__)


@base_router.get("/", tags=["root"])
async def root():
    """
    Root endpoint that returns a welcome message.
    """
    return Response(content="Welcome to the Auto-GPT Forge")


@base_router.get("/heartbeat", tags=["server"])
async def check_server_status():
    """
    Check if the server is running.
    """
    return Response(content="Server is running.", status_code=200)


@base_router.get("/", tags=["root"])
async def root():
    """
    Root endpoint that returns a welcome message.
    """
    return Response(content="Welcome to the Auto-GPT Forge")


@base_router.get("/heartbeat", tags=["server"])
async def check_server_status():
    """
    Check if the server is running.
    """
    return Response(content="Server is running.", status_code=200)


@base_router.post("/agent/tasks", tags=["agent"], response_model=Task)
@tracing("Creating new task", is_create_task=True)
async def create_agent_task(request: Request, task_request: TaskRequestBody) -> Task:
    """
    Creates a new task using the provided TaskRequestBody and returns a Task.

    Args:
        request (Request): FastAPI request object.
        task (TaskRequestBody): The task request containing input and additional input data.

    Returns:
        Task: A new task with task_id, input, additional_input, and empty lists for artifacts and steps.

    Example:
        Request (TaskRequestBody defined in schema.py):
            {
                "input": "Write the words you receive to the file 'output.txt'.",
                "additional_input": "python/code"
            }

        Response (Task defined in schema.py):
            {
                "task_id": "50da533e-3904-4401-8a07-c49adf88b5eb",
                "input": "Write the word 'Washington' to a .txt file",
                "additional_input": "python/code",
                "artifacts": [],
            }
    """
    agent = request["agent"]

    try:
        task_request = await agent.create_task(task_request)
        return Response(
            content=task_request.json(),
            status_code=200,
            media_type="application/json",
        )
    except NotFoundError:
        return Response(
            content=json.dumps({"error": "Task not found"}),
            status_code=404,
            media_type="application/json",
        )
    except Exception:
        return Response(
            content=json.dumps({"error": "Internal server error"}),
            status_code=500,
            media_type="application/json",
        )


@base_router.get("/agent/tasks", tags=["agent"], response_model=TaskListResponse)
async def list_agent_tasks(
    request: Request,
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(10, ge=1, alias="pageSize"),
) -> TaskListResponse:
    """
    Retrieves a paginated list of all tasks.

    Args:
        request (Request): FastAPI request object.
        page (int, optional): The page number for pagination. Defaults to 1.
        page_size (int, optional): The number of tasks per page for pagination. Defaults to 10.

    Returns:
        TaskListResponse: A response object containing a list of tasks and pagination details.

    Example:
        Request:
            GET /agent/tasks?page=1&pageSize=10

        Response (TaskListResponse defined in schema.py):
            {
                "items": [
                    {
                        "input": "Write the word 'Washington' to a .txt file",
                        "additional_input": null,
                        "task_id": "50da533e-3904-4401-8a07-c49adf88b5eb",
                        "artifacts": [],
                        "steps": []
                    },
                    ...
                ],
                "pagination": {
                    "total": 100,
                    "pages": 10,
                    "current": 1,
                    "pageSize": 10
                }
            }
    """
    agent = request["agent"]
    try:
        tasks = await agent.list_tasks(page, page_size)
        return Response(
            content=tasks.json(),
            status_code=200,
            media_type="application/json",
        )
    except NotFoundError:
        return Response(
            content=json.dumps({"error": "Task not found"}),
            status_code=404,
            media_type="application/json",
        )
    except Exception:
        return Response(
            content=json.dumps({"error": "Internal server error"}),
            status_code=500,
            media_type="application/json",
        )


@base_router.get("/agent/tasks/{task_id}", tags=["agent"], response_model=Task)
@tracing("Getting task details")
async def get_agent_task(request: Request, task_id: str) -> Task:
    """
    Gets the details of a task by ID.

    Args:
        request (Request): FastAPI request object.
        task_id (str): The ID of the task.

    Returns:
        Task: The task with the given ID.

    Example:
        Request:
            GET /agent/tasks/50da533e-3904-4401-8a07-c49adf88b5eb

        Response (Task defined in schema.py):
            {
                "input": "Write the word 'Washington' to a .txt file",
                "additional_input": null,
                "task_id": "50da533e-3904-4401-8a07-c49adf88b5eb",
                "artifacts": [
                    {
                        "artifact_id": "7a49f31c-f9c6-4346-a22c-e32bc5af4d8e",
                        "file_name": "output.txt",
                        "agent_created": true,
                        "uri": "file://50da533e-3904-4401-8a07-c49adf88b5eb/output.txt"
                    }
                ],
                "steps": [
                    {
                        "task_id": "50da533e-3904-4401-8a07-c49adf88b5eb",
                        "step_id": "6bb1801a-fd80-45e8-899a-4dd723cc602e",
                        "input": "Write the word 'Washington' to a .txt file",
                        "additional_input": "challenge:write_to_file",
                        "name": "Write to file",
                        "status": "completed",
                        "output": "I am going to use the write_to_file command and write Washington to a file called output.txt <write_to_file('output.txt', 'Washington')>",
                        "additional_output": "Do you want me to continue?",
                        "artifacts": [
                            {
                                "artifact_id": "7a49f31c-f9c6-4346-a22c-e32bc5af4d8e",
                                "file_name": "output.txt",
                                "agent_created": true,
                                "uri": "file://50da533e-3904-4401-8a07-c49adf88b5eb/output.txt"
                            }
                        ],
                        "is_last": true
                    }
                ]
            }
    """
    agent = request["agent"]
    try:
        task = await agent.get_task(task_id)
        return Response(
            content=task.json(),
            status_code=200,
            media_type="application/json",
        )
    except NotFoundError:
        return Response(
            content=json.dumps({"error": "Task not found"}),
            status_code=404,
            media_type="application/json",
        )
    except Exception:
        return Response(
            content=json.dumps({"error": "Internal server error"}),
            status_code=500,
            media_type="application/json",
        )


@base_router.get(
    "/agent/tasks/{task_id}/steps", tags=["agent"], response_model=TaskStepsListResponse
)
async def list_agent_task_steps(
    request: Request,
    task_id: str,
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(10, ge=1, alias="pageSize"),
) -> TaskStepsListResponse:
    """
    Retrieves a paginated list of steps associated with a specific task.

    Args:
        request (Request): FastAPI request object.
        task_id (str): The ID of the task.
        page (int, optional): The page number for pagination. Defaults to 1.
        page_size (int, optional): The number of steps per page for pagination. Defaults to 10.

    Returns:
        TaskStepsListResponse: A response object containing a list of steps and pagination details.

    Example:
        Request:
            GET /agent/tasks/50da533e-3904-4401-8a07-c49adf88b5eb/steps?page=1&pageSize=10

        Response (TaskStepsListResponse defined in schema.py):
            {
                "items": [
                    {
                        "task_id": "50da533e-3904-4401-8a07-c49adf88b5eb",
                        "step_id": "step1_id",
                        ...
                    },
                    ...
                ],
                "pagination": {
                    "total": 100,
                    "pages": 10,
                    "current": 1,
                    "pageSize": 10
                }
            }
    """
    agent = request["agent"]
    try:
        steps = await agent.list_steps(task_id, page, page_size)
        return Response(
            content=steps.json(),
            status_code=200,
            media_type="application/json",
        )
    except NotFoundError:
        return Response(
            content=json.dumps({"error": "Task not found"}),
            status_code=404,
            media_type="application/json",
        )
    except Exception:
        return Response(
            content=json.dumps({"error": "Internal server error"}),
            status_code=500,
            media_type="application/json",
        )


@base_router.post("/agent/tasks/{task_id}/steps", tags=["agent"], response_model=Step)
@tracing("Creating and executing Step")
async def execute_agent_task_step(
    request: Request, task_id: str, step: StepRequestBody
) -> Step:
    """
    Executes the next step for a specified task based on the current task status and returns the
    executed step with additional feedback fields.

    Depending on the current state of the task, the following scenarios are supported:

    1. No steps exist for the task.
    2. There is at least one step already for the task, and the task does not have a completed step marked as `last_step`.
    3. There is a completed step marked as `last_step` already on the task.

    In each of these scenarios, a step object will be returned with two additional fields: `output` and `additional_output`.
    - `output`: Provides the primary response or feedback to the user.
    - `additional_output`: Supplementary information or data. Its specific content is not strictly defined and can vary based on the step or agent's implementation.

    Args:
        request (Request): FastAPI request object.
        task_id (str): The ID of the task.
        step (StepRequestBody): The details for executing the step.

    Returns:
        Step: Details of the executed step with additional feedback.

    Example:
        Request:
            POST /agent/tasks/50da533e-3904-4401-8a07-c49adf88b5eb/steps
            {
                "input": "Step input details...",
                ...
            }

        Response:
            {
                "task_id": "50da533e-3904-4401-8a07-c49adf88b5eb",
                "step_id": "step1_id",
                "output": "Primary feedback...",
                "additional_output": "Supplementary details...",
                ...
            }
    """
    agent = request["agent"]
    try:
        step = await agent.create_and_execute_step(task_id, step)
        return Response(
            content=step.json(),
            status_code=200,
            media_type="application/json",
        )
    except NotFoundError:
        return Response(
            content=json.dumps({"error": f"Task not found {task_id}"}),
            status_code=404,
            media_type="application/json",
        )
    except Exception as e:
        LOG.exception("Error whilst trying to execute a test")
        return Response(
            content=json.dumps({"error": "Internal server error"}),
            status_code=500,
            media_type="application/json",
        )


@base_router.get(
    "/agent/tasks/{task_id}/steps/{step_id}", tags=["agent"], response_model=Step
)
@tracing("Getting Step Details")
async def get_agent_task_step(request: Request, task_id: str, step_id: str) -> Step:
    """
    Retrieves the details of a specific step for a given task.

    Args:
        request (Request): FastAPI request object.
        task_id (str): The ID of the task.
        step_id (str): The ID of the step.

    Returns:
        Step: Details of the specific step.

    Example:
        Request:
            GET /agent/tasks/50da533e-3904-4401-8a07-c49adf88b5eb/steps/step1_id

        Response:
            {
                "task_id": "50da533e-3904-4401-8a07-c49adf88b5eb",
                "step_id": "step1_id",
                ...
            }
    """
    agent = request["agent"]
    try:
        step = await agent.get_step(task_id, step_id)
        return Response(content=step.json(), status_code=200)
    except NotFoundError:
        return Response(
            content=json.dumps({"error": "Task not found"}),
            status_code=404,
            media_type="application/json",
        )
    except Exception:
        return Response(
            content=json.dumps({"error": "Internal server error"}),
            status_code=500,
            media_type="application/json",
        )


@base_router.get(
    "/agent/tasks/{task_id}/artifacts",
    tags=["agent"],
    response_model=TaskArtifactsListResponse,
)
@tracing("Listing Task Artifacts")
async def list_agent_task_artifacts(
    request: Request,
    task_id: str,
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(10, ge=1, alias="pageSize"),
) -> TaskArtifactsListResponse:
    """
    Retrieves a paginated list of artifacts associated with a specific task.

    Args:
        request (Request): FastAPI request object.
        task_id (str): The ID of the task.
        page (int, optional): The page number for pagination. Defaults to 1.
        page_size (int, optional): The number of items per page for pagination. Defaults to 10.

    Returns:
        TaskArtifactsListResponse: A response object containing a list of artifacts and pagination details.

    Example:
        Request:
            GET /agent/tasks/50da533e-3904-4401-8a07-c49adf88b5eb/artifacts?page=1&pageSize=10

        Response (TaskArtifactsListResponse defined in schema.py):
            {
                "items": [
                    {"artifact_id": "artifact1_id", ...},
                    {"artifact_id": "artifact2_id", ...},
                    ...
                ],
                "pagination": {
                    "total": 100,
                    "pages": 10,
                    "current": 1,
                    "pageSize": 10
                }
            }
    """
    agent = request["agent"]
    try:
        artifacts = await agent.list_artifacts(task_id, page, page_size)
        return artifacts
    except NotFoundError:
        return Response(
            content=json.dumps({"error": "Task not found"}),
            status_code=404,
            media_type="application/json",
        )
    except Exception:
        return Response(
            content=json.dumps({"error": "Internal server error"}),
            status_code=500,
            media_type="application/json",
        )


@base_router.post(
    "/agent/tasks/{task_id}/artifacts", tags=["agent"], response_model=Artifact
)
@tracing("Uploading task artifact")
async def upload_agent_task_artifacts(
    request: Request,
    task_id: str,
    file: UploadFile | None = None,
    uri: str | None = None,
) -> Artifact:
    """
    Uploads an artifact for a specific task using either a provided file or a URI.
    At least one of the parameters, `file` or `uri`, must be specified. The `uri` can point to
    cloud storage resources such as S3, GCS, etc., or to other resources like FTP or HTTP.

    To check the supported URI types for the agent, use the `/agent/artifacts/uris` endpoint.

    Args:
        request (Request): FastAPI request object.
        task_id (str): The ID of the task.
        file (UploadFile, optional): The uploaded file. Defaults to None.
        uri (str, optional): The URI pointing to the resource. Defaults to None.

    Returns:
        Artifact: Details of the uploaded artifact.

    Note:
        Either `file` or `uri` must be provided. If both are provided, the behavior depends on
        the agent's implementation. If neither is provided, the function will return an error.
    Example:
        Request:
            POST /agent/tasks/50da533e-3904-4401-8a07-c49adf88b5eb/artifacts
            File: <uploaded_file>
            OR
            URI: "s3://path/to/artifact"

        Response:
            {
                "artifact_id": "artifact1_id",
                ...
            }
    """
    agent = request["agent"]
    if file is None and uri is None:
        return Response(
            content=json.dumps({"error": "Either file or uri must be specified"}),
            status_code=404,
            media_type="application/json",
        )
    if file is not None and uri is not None:
        return Response(
            content=json.dumps(
                {"error": "Both file and uri cannot be specified at the same time"}
            ),
            status_code=404,
            media_type="application/json",
        )
    if uri is not None and not uri.startswith(("http://", "https://", "file://")):
        return Response(
            content=json.dumps({"error": "URI must start with http, https or file"}),
            status_code=404,
            media_type="application/json",
        )
    try:
        artifact = await agent.create_artifact(task_id, file, uri)
        return Response(
            content=artifact.json(),
            status_code=200,
            media_type="application/json",
        )
    except NotFoundError:
        return Response(
            content=json.dumps({"error": "Task not found"}),
            status_code=404,
            media_type="application/json",
        )
    except Exception:
        return Response(
            content=json.dumps({"error": "Internal server error"}),
            status_code=500,
            media_type="application/json",
        )


@base_router.get(
    "/agent/tasks/{task_id}/artifacts/{artifact_id}", tags=["agent"], response_model=str
)
@tracing("Downloading task artifact")
async def download_agent_task_artifact(
    request: Request, task_id: str, artifact_id: str
) -> FileResponse:
    """
    Downloads an artifact associated with a specific task.

    Args:
        request (Request): FastAPI request object.
        task_id (str): The ID of the task.
        artifact_id (str): The ID of the artifact.

    Returns:
        FileResponse: The downloaded artifact file.

    Example:
        Request:
            GET /agent/tasks/50da533e-3904-4401-8a07-c49adf88b5eb/artifacts/artifact1_id

        Response:
            <file_content_of_artifact>
    """
    agent = request["agent"]
    try:
        return await agent.get_artifact(task_id, artifact_id)
    except NotFoundError:
        return Response(
            content=json.dumps(
                {
                    "error": f"Artifact not found - task_id: {task_id}, artifact_id: {artifact_id}"
                }
            ),
            status_code=404,
            media_type="application/json",
        )
    except Exception:
        return Response(
            content=json.dumps(
                {
                    "error": f"Internal server error - task_id: {task_id}, artifact_id: {artifact_id}"
                }
            ),
            status_code=500,
            media_type="application/json",
        )
