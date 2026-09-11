from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import requests


ROOT = Path(__file__).resolve().parents[1]
V2_ROOT = ROOT / "data" / "release" / "v2"
METADATA_PATH = V2_ROOT / "dataset-metadata.json"
OUT = ROOT / "data" / "audits" / "kaggle_v2_databundle_metadata.json"

DATASET = "taeyangg4/south-korea-power-grid-5-minute"
OWNER = "taeyangg4"
DATASET_SLUG = "south-korea-power-grid-5-minute"
DATASET_NUMERIC_ID = 11_964_918
APPROVED_VERSION = 2

KAGGLE_ORIGIN = "https://www.kaggle.com"
GET_DATASET_BASICS = "/api/i/datasets.DatasetDetailService/GetDatasetBasics"
GET_DATABUNDLE_EXTERNAL = "/api/i/datasets.databundles.DatabundleService/GetDatabundleExternal"
GET_DATABUNDLE_EXTERNAL_CHILDREN = (
    "/api/i/datasets.databundles.DatabundleService/GetDatabundleExternalChildren"
)
GET_DATABUNDLE_EXTERNAL_COLUMNS = (
    "/api/i/datasets.databundles.DatabundleService/GetDatabundleExternalColumns"
)
GET_DATABUNDLE_EXTERNAL_COLUMNS_BY_PATH = (
    "/api/i/datasets.databundles.DatabundleService/GetDatabundleExternalColumnsByFirestorePath"
)
UPDATE_DATABUNDLE_METADATA_EXTERNAL = (
    "/api/i/datasets.databundles.DatabundleService/UpdateDatabundleMetadataExternal"
)
GET_DATASET_USABILITY = "/api/i/datasets.DatasetDetailService/GetDatasetUsabilityRating"


class KaggleMetadataError(RuntimeError):
    pass


class _Response(Protocol):
    status_code: int
    text: str

    def json(self) -> Any: ...

    def raise_for_status(self) -> None: ...


class _Session(Protocol):
    def post(
        self,
        url: str,
        *,
        json: dict[str, Any],
        timeout: float,
    ) -> _Response: ...


@dataclass(frozen=True)
class LiveDatasetContext:
    dataset_id: int
    dataset_version_id: int
    databundle_version_id: int
    version_number: int
    root_firestore_path: str
    file_firestore_paths: dict[str, str]
    table_shapes: dict[str, tuple[int, int]]


def load_metadata() -> dict[str, Any]:
    return json.loads(METADATA_PATH.read_text(encoding="ascii"))


def resources_by_name() -> dict[str, dict[str, Any]]:
    metadata = load_metadata()
    resources = metadata.get("resources") or []
    result: dict[str, dict[str, Any]] = {}
    for resource in resources:
        item = dict(resource)
        schema = dict(item.get("schema") or {})
        fields = []
        for raw_field in schema.get("fields") or []:
            field = dict(raw_field)
            field["description"] = str(
                field.get("description") or field.get("title") or ""
            )
            fields.append(field)
        if fields:
            schema["fields"] = fields
            item["schema"] = schema
        name = str(item["path"])
        result[name] = item
    return result


def _post_json(
    session: _Session,
    endpoint: str,
    payload: dict[str, Any],
    *,
    timeout: float = 30.0,
) -> dict[str, Any]:
    response = session.post(
        f"{KAGGLE_ORIGIN}{endpoint}",
        json=payload,
        timeout=timeout,
    )
    try:
        response.raise_for_status()
    except Exception as exc:
        body = getattr(response, "text", "") or ""
        compact = " ".join(body.split())[:500]
        detail = f": {compact}" if compact else ""
        raise KaggleMetadataError(
            f"Kaggle request failed for {endpoint} "
            f"(HTTP {getattr(response, 'status_code', '?')}){detail}"
        ) from exc
    try:
        value = response.json()
    except Exception as exc:
        raise KaggleMetadataError(
            f"Kaggle returned a non-JSON response for {endpoint}"
        ) from exc
    if not isinstance(value, dict):
        raise KaggleMetadataError(
            f"Kaggle returned an unexpected response for {endpoint}"
        )
    if int(value.get("code", 0) or 0) >= 400:
        raise KaggleMetadataError(
            f"Kaggle rejected {endpoint}: {value.get('message', 'unknown error')}"
        )
    return value


def _verification_info(context: LiveDatasetContext) -> dict[str, int]:
    return {
        "databundleVersionId": context.databundle_version_id,
        "datasetId": context.dataset_id,
    }


def load_live_context(
    session: _Session,
    *,
    version_number: int = APPROVED_VERSION,
) -> LiveDatasetContext:
    basics = _post_json(
        session,
        GET_DATASET_BASICS,
        {
            "ownerSlug": OWNER,
            "datasetSlug": DATASET_SLUG,
            "datasetVersionNumber": version_number,
        },
    )
    dataset_id = int(basics.get("datasetId", 0) or 0)
    if dataset_id != DATASET_NUMERIC_ID:
        raise KaggleMetadataError(
            f"dataset numeric id changed: expected {DATASET_NUMERIC_ID}, got {dataset_id}"
        )
    if basics.get("slug") not in {None, "", DATASET_SLUG}:
        raise KaggleMetadataError("dataset slug changed")

    live_version = int(basics.get("datasetVersionNumber", 0) or 0)
    if live_version != version_number:
        raise KaggleMetadataError(
            f"expected dataset version {version_number}, got {live_version}"
        )
    dataset_version_id = int(basics.get("datasetVersionId", 0) or 0)
    data = basics.get("data")
    if not isinstance(data, dict):
        raise KaggleMetadataError("dataset has no current databundle")
    databundle_version_id = int(data.get("versionId", 0) or 0)
    if dataset_version_id <= 0 or databundle_version_id <= 0:
        raise KaggleMetadataError("dataset version identifiers are incomplete")

    provisional = LiveDatasetContext(
        dataset_id=dataset_id,
        dataset_version_id=dataset_version_id,
        databundle_version_id=databundle_version_id,
        version_number=live_version,
        root_firestore_path="",
        file_firestore_paths={},
        table_shapes={},
    )
    external = _post_json(
        session,
        GET_DATABUNDLE_EXTERNAL,
        {"verificationInfo": _verification_info(provisional)},
    )
    data_source = external.get("dataSource")
    if not isinstance(data_source, dict):
        raise KaggleMetadataError("Data Explorer returned no data source")
    if int(data_source.get("sourceId", 0) or 0) != dataset_id:
        raise KaggleMetadataError("Data Explorer dataset id changed")
    if data_source.get("slug") not in {None, "", DATASET_SLUG}:
        raise KaggleMetadataError("Data Explorer dataset slug changed")
    if int(data_source.get("versionNumber", 0) or 0) != live_version:
        raise KaggleMetadataError("Data Explorer version number disagrees with dataset basics")

    root_path = str(data_source.get("path") or "")
    version = data_source.get("databundleVersion")
    if not root_path or not isinstance(version, dict):
        raise KaggleMetadataError("Data Explorer current version tree is incomplete")
    if int(version.get("legacyEntityId", 0) or 0) != databundle_version_id:
        raise KaggleMetadataError("Data Explorer databundle version id changed")
    version_info = version.get("datasetVersionInfo")
    if (
        not isinstance(version_info, dict)
        or int(version_info.get("datasetVersionId", 0) or 0) != dataset_version_id
    ):
        raise KaggleMetadataError("Data Explorer dataset version id changed")

    fileset_info = version.get("filesetInfo")
    files_container = fileset_info.get("files") if isinstance(fileset_info, dict) else None
    files = files_container.get("children") if isinstance(files_container, dict) else None
    if not isinstance(files, list):
        raise KaggleMetadataError("Data Explorer file listing is unavailable")

    file_paths: dict[str, str] = {}
    table_shapes: dict[str, tuple[int, int]] = {}
    for item in files:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        firestore_path = str(item.get("path") or "")
        if not name or not firestore_path:
            raise KaggleMetadataError("Data Explorer returned a file without name/path")
        file_paths[name] = firestore_path
        table_info = item.get("tableInfo")
        if isinstance(table_info, dict):
            table_columns = table_info.get("tableColumns")
            total_columns = int(table_info.get("totalColumns", 0) or 0)
            if total_columns == 0 and isinstance(table_columns, dict):
                total_columns = int(table_columns.get("totalChildren", 0) or 0)
            table_shapes[name] = (
                int(table_info.get("totalRows", 0) or 0),
                total_columns,
            )

    expected_files = set(resources_by_name())
    if set(file_paths) != expected_files:
        raise KaggleMetadataError(
            "live Kaggle file set changed: "
            f"expected {sorted(expected_files)}, got {sorted(file_paths)}"
        )

    return LiveDatasetContext(
        dataset_id=dataset_id,
        dataset_version_id=dataset_version_id,
        databundle_version_id=databundle_version_id,
        version_number=live_version,
        root_firestore_path=root_path,
        file_firestore_paths=file_paths,
        table_shapes=table_shapes,
    )


def _column_updates(
    session: _Session,
    context: LiveDatasetContext,
    *,
    file_path: str,
    expected_fields: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    verification = _verification_info(context)
    base = _post_json(
        session,
        GET_DATABUNDLE_EXTERNAL_COLUMNS,
        {"verificationInfo": verification, "firestorePath": file_path},
    )
    columns = base.get("columns")
    if not isinstance(columns, list):
        raise KaggleMetadataError("Kaggle column listing is unavailable")
    ordered = sorted(
        (item for item in columns if isinstance(item, dict)),
        key=lambda item: int(item.get("order", 0) or 0),
    )
    live_names = [str(item.get("name") or "") for item in ordered]
    expected_names = [str(item["name"]) for item in expected_fields]
    if live_names != expected_names:
        raise KaggleMetadataError(
            f"column order changed: expected {expected_names}, got {live_names}"
        )
    paths = [str(item.get("firestorePath") or "") for item in ordered]
    if any(not path for path in paths) or len(set(paths)) != len(paths):
        raise KaggleMetadataError("invalid column Firestore paths")

    hydrated = _post_json(
        session,
        GET_DATABUNDLE_EXTERNAL_COLUMNS_BY_PATH,
        {"verificationInfo": verification, "firestorePaths": paths},
    )
    full_columns = hydrated.get("columns")
    if not isinstance(full_columns, list):
        raise KaggleMetadataError("hydrated column metadata is unavailable")
    by_path = {
        str(item.get("path") or item.get("firestorePath") or ""): item
        for item in full_columns
        if isinstance(item, dict)
    }
    if set(by_path) != set(paths):
        raise KaggleMetadataError("hydrated column paths changed")

    description_by_name = {
        str(field["name"]): str(field["description"]) for field in expected_fields
    }
    result: list[dict[str, Any]] = []
    for item, path in zip(ordered, paths, strict=True):
        name = str(item["name"])
        full = by_path[path]
        info = full.get("tableColumnInfo")
        if not isinstance(info, dict):
            raise KaggleMetadataError(f"{name}: tableColumnInfo is missing")
        harmonized_type = info.get("type", "STRING")
        extended_type = info.get("extendedType", "EXTENDED_DATA_TYPE_UNSPECIFIED")
        if not isinstance(harmonized_type, str) or not harmonized_type:
            raise KaggleMetadataError(f"{name}: harmonized type is invalid")
        if not isinstance(extended_type, str) or not extended_type:
            raise KaggleMetadataError(f"{name}: extended type is invalid")
        result.append(
            {
                "firestorePath": path,
                "description": description_by_name[name],
                "type": harmonized_type,
                "extendedType": extended_type,
            }
        )
    return result


def build_update_plan(
    session: _Session,
    context: LiveDatasetContext,
) -> list[dict[str, Any]]:
    resources = resources_by_name()
    verification = _verification_info(context)
    updates: list[dict[str, Any]] = []
    for name, resource in resources.items():
        file_path = context.file_firestore_paths[name]
        fields = (resource.get("schema") or {}).get("fields") or []
        columns = (
            _column_updates(
                session,
                context,
                file_path=file_path,
                expected_fields=fields,
            )
            if fields
            else []
        )
        updates.append(
            {
                "verificationInfo": verification,
                "firestorePath": file_path,
                "description": str(resource.get("description") or ""),
                "columns": columns,
            }
        )
    return updates


def get_live_metadata_coverage(
    session: _Session,
    context: LiveDatasetContext,
) -> dict[str, Any]:
    resources = resources_by_name()
    verification = _verification_info(context)
    root_children = _post_json(
        session,
        GET_DATABUNDLE_EXTERNAL_CHILDREN,
        {
            "verificationInfo": verification,
            "firestorePath": context.root_firestore_path,
            "offset": 0,
            "count": max(100, len(resources)),
            "depth": 1,
        },
    )
    live_files = root_children.get("files")
    if not isinstance(live_files, list):
        raise KaggleMetadataError("Kaggle root file metadata is unavailable")
    descriptions_by_file = {
        str(item.get("name") or ""): str(item.get("description") or "")
        for item in live_files
        if isinstance(item, dict) and item.get("name")
    }
    if set(descriptions_by_file) != set(resources):
        raise KaggleMetadataError(
            "Kaggle root file metadata set changed: "
            f"expected {sorted(resources)}, got {sorted(descriptions_by_file)}"
        )

    present_files = sum(bool(description.strip()) for description in descriptions_by_file.values())
    exact_files = sum(
        descriptions_by_file[name] == str(resource.get("description") or "")
        for name, resource in resources.items()
    )
    target_columns = 0
    present_columns = 0
    exact_columns = 0
    per_table: dict[str, dict[str, int]] = {}
    for name, resource in resources.items():
        fields = (resource.get("schema") or {}).get("fields") or []
        if not fields:
            continue
        target_columns += len(fields)
        file_path = context.file_firestore_paths[name]
        base = _post_json(
            session,
            GET_DATABUNDLE_EXTERNAL_COLUMNS,
            {"verificationInfo": verification, "firestorePath": file_path},
        )
        columns = base.get("columns")
        if not isinstance(columns, list):
            raise KaggleMetadataError(f"{name}: Kaggle column listing is unavailable")
        ordered = sorted(
            (item for item in columns if isinstance(item, dict)),
            key=lambda item: int(item.get("order", 0) or 0),
        )
        live_names = [str(item.get("name") or "") for item in ordered]
        expected_names = [str(field["name"]) for field in fields]
        if live_names != expected_names:
            raise KaggleMetadataError(
                f"{name}: live column order changed: expected {expected_names}, got {live_names}"
            )
        paths = [str(item.get("firestorePath") or "") for item in ordered]
        hydrated = _post_json(
            session,
            GET_DATABUNDLE_EXTERNAL_COLUMNS_BY_PATH,
            {"verificationInfo": verification, "firestorePaths": paths},
        )
        full_columns = hydrated.get("columns")
        if not isinstance(full_columns, list):
            raise KaggleMetadataError(f"{name}: hydrated column metadata is unavailable")
        by_path = {
            str(item.get("path") or item.get("firestorePath") or ""): item
            for item in full_columns
            if isinstance(item, dict)
        }
        present_for_table = 0
        exact_for_table = 0
        for item, field, path in zip(ordered, fields, paths, strict=True):
            full = by_path[path]
            info = full.get("tableColumnInfo")
            nested_description = info.get("description") if isinstance(info, dict) else None
            live_description = str(full.get("description") or nested_description or "")
            if live_description.strip():
                present_for_table += 1
            if live_description == str(field["description"]):
                exact_for_table += 1
        present_columns += present_for_table
        exact_columns += exact_for_table
        per_table[name] = {
            "present_column_descriptions": present_for_table,
            "exact_column_descriptions": exact_for_table,
            "target_column_descriptions": len(fields),
        }

    return {
        "target_file_descriptions": len(resources),
        "present_file_descriptions": present_files,
        "exact_file_descriptions": exact_files,
        "target_column_descriptions": target_columns,
        "present_column_descriptions": present_columns,
        "exact_column_descriptions": exact_columns,
        "all_file_descriptions_present": present_files == len(resources),
        "all_file_descriptions_exact": exact_files == len(resources),
        "all_column_descriptions_present": present_columns == target_columns,
        "all_column_descriptions_exact": exact_columns == target_columns,
        "metadata_complete": present_files == len(resources)
        and present_columns == target_columns,
        "metadata_exact": exact_files == len(resources)
        and exact_columns == target_columns,
        "per_table": per_table,
    }


def get_usability_rating(session: _Session) -> dict[str, Any]:
    response = _post_json(
        session,
        GET_DATASET_USABILITY,
        {"datasetId": DATASET_NUMERIC_ID},
    )
    rating = response.get("rating")
    if not isinstance(rating, dict):
        raise KaggleMetadataError("Kaggle usability rating is unavailable")
    return rating


def _authenticated_session():
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except ImportError as exc:
        raise KaggleMetadataError("Kaggle CLI package is required") from exc
    api = KaggleApi()
    api.authenticate()
    client = api.build_kaggle_client()
    http_client = client.http_client()
    http_client._init_session()
    session = http_client._session
    if session is None:
        raise KaggleMetadataError("Kaggle CLI did not initialize an authenticated session")
    # The public Kaggle SDK authenticates API calls with the bearer token, but
    # the Data Explorer metadata endpoint is hosted on www.kaggle.com and also
    # requires the browser-style XSRF cookie/header pair. Prime that pair with
    # a harmless GET while retaining the SDK bearer auth on the same session.
    bootstrap = session.get(KAGGLE_ORIGIN, timeout=30)
    bootstrap.raise_for_status()
    xsrf_token = session.cookies.get("XSRF-TOKEN")
    if not xsrf_token:
        raise KaggleMetadataError("Kaggle did not issue an XSRF token")
    session.headers["X-XSRF-TOKEN"] = xsrf_token
    return session


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Synchronize V2 file and column descriptions into Kaggle Data Explorer. "
            "Default is read-only; pass --apply to write the validated plan."
        )
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--version", type=int, default=APPROVED_VERSION)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.version != APPROVED_VERSION:
        raise KaggleMetadataError(
            f"Refusing version {args.version}; only approved V2 may be maintained"
        )

    public_session = requests.Session()
    public_context = load_live_context(public_session, version_number=args.version)
    authenticated_session = _authenticated_session()
    authenticated_context = load_live_context(
        authenticated_session,
        version_number=public_context.version_number,
    )
    if (
        authenticated_context.dataset_version_id != public_context.dataset_version_id
        or authenticated_context.databundle_version_id != public_context.databundle_version_id
    ):
        raise KaggleMetadataError(
            "authenticated Kaggle view disagrees with the current public V2 identifiers"
        )

    updates = build_update_plan(authenticated_session, authenticated_context)
    before = get_live_metadata_coverage(public_session, public_context)
    output: dict[str, Any] = {
        "dataset": DATASET,
        "mode": "apply" if args.apply else "dry-run",
        "context": {
            "dataset_numeric_id": public_context.dataset_id,
            "dataset_version_id": public_context.dataset_version_id,
            "databundle_version_id": public_context.databundle_version_id,
            "version_number": public_context.version_number,
            "file_count": len(public_context.file_firestore_paths),
            "table_shapes": public_context.table_shapes,
        },
        "plan": {
            "files": len(updates),
            "columns": sum(len(update["columns"]) for update in updates),
        },
        "coverage_before": before,
        "legacy_dataset_id_only_usability_before": get_usability_rating(public_session),
    }

    if args.apply:
        responses = [
            _post_json(authenticated_session, UPDATE_DATABUNDLE_METADATA_EXTERNAL, update)
            for update in updates
        ]
        output["update_calls"] = len(responses)

        after = before
        for _ in range(5):
            time.sleep(2)
            after = get_live_metadata_coverage(requests.Session(), public_context)
            if after["metadata_complete"]:
                break
        output["coverage_after"] = after
        output["legacy_dataset_id_only_usability_after"] = get_usability_rating(
            requests.Session()
        )

    OUT.write_text(
        json.dumps(output, ensure_ascii=True, indent=2, sort_keys=True),
        encoding="ascii",
    )
    print(json.dumps(output, ensure_ascii=True, indent=2, sort_keys=True))
    print(f"WROTE {OUT}")

    if args.apply and not output["coverage_after"]["metadata_complete"]:
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KaggleMetadataError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
