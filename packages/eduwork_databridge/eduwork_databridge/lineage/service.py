import json
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from eduwork_databridge.db.models.control import LineageEdge, LineageNode


@dataclass(frozen=True)
class LineageTrace:
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class LineageService:
    def __init__(self, session: Session, event_root: Path = Path("var/lineage")) -> None:
        self.session = session
        self.event_root = event_root.expanduser().resolve()
        self.event_root.mkdir(parents=True, exist_ok=True)

    def _node(
        self,
        organization_id: uuid.UUID,
        node_type: str,
        namespace: str,
        name: str,
        facets: dict[str, Any] | None = None,
    ) -> LineageNode:
        node = self.session.scalar(
            select(LineageNode).where(
                LineageNode.organization_id == organization_id,
                LineageNode.node_type == node_type,
                LineageNode.namespace == namespace,
                LineageNode.name == name,
            )
        )
        if node is None:
            node = LineageNode(
                organization_id=organization_id,
                node_type=node_type,
                namespace=namespace,
                name=name,
                facets_json=facets or {},
            )
            self.session.add(node)
            self.session.flush()
        return node

    def connect(
        self,
        organization_id: uuid.UUID,
        from_node: LineageNode,
        to_node: LineageNode,
        relation_type: str,
        field_mapping: dict[str, Any] | None = None,
    ) -> LineageEdge:
        edge = LineageEdge(
            organization_id=organization_id,
            from_node_id=from_node.id,
            to_node_id=to_node.id,
            relation_type=relation_type,
            field_mapping_json=field_mapping or {},
        )
        self.session.add(edge)
        self.session.flush()
        return edge

    def record_mapping(
        self,
        organization_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        mapping_id: str,
        mapping_version: str,
        rules: list[dict[str, Any]],
    ) -> list[uuid.UUID]:
        source = self._node(
            organization_id,
            "dataset",
            "eduwork.raw",
            str(snapshot_id),
            {"snapshot_id": str(snapshot_id)},
        )
        job = self._node(
            organization_id,
            "job",
            "eduwork.mapping",
            f"{mapping_id}:{mapping_version}",
            {"mapping_id": mapping_id, "version": mapping_version},
        )
        self.connect(organization_id, source, job, "used")
        node_ids = [source.id, job.id]
        for sequence, rule in enumerate(rules, start=1):
            target = self._node(
                organization_id,
                "field",
                "eduwork.canonical",
                f"{mapping_id}.{rule['target']}",
                {"target_field": rule["target"]},
            )
            self.connect(
                organization_id,
                job,
                target,
                "generated",
                {
                    "sequence": sequence,
                    "source": rule.get("source"),
                    "target": rule["target"],
                    "transform": rule.get("transform"),
                },
            )
            node_ids.append(target.id)
        self.session.commit()
        return node_ids

    def record_export(
        self,
        organization_id: uuid.UUID,
        mart_id: uuid.UUID,
        export_id: uuid.UUID,
        fields: list[str],
    ) -> list[uuid.UUID]:
        mart = self._node(
            organization_id,
            "dataset",
            "eduwork.mart",
            str(mart_id),
            {"mart_snapshot_id": str(mart_id)},
        )
        export = self._node(
            organization_id,
            "dataset",
            "eduwork.export",
            str(export_id),
            {"export_snapshot_id": str(export_id), "fields": fields},
        )
        edge = self.connect(
            organization_id,
            mart,
            export,
            "derived_from",
            {field: field for field in fields},
        )
        self.session.commit()
        return [mart.id, export.id, edge.id]

    def emit_openlineage_event(
        self,
        organization_id: uuid.UUID,
        job_name: str,
        run_id: uuid.UUID,
        event_type: str,
        inputs: list[str],
        outputs: list[str],
    ) -> Path:
        event = {
            "eventType": event_type,
            "eventTime": datetime.now(UTC).isoformat(),
            "producer": "https://github.com/imtiazither/eduwork-databridge",
            "schemaURL": "https://openlineage.io/spec/2-0-2/OpenLineage.json",
            "run": {
                "runId": str(run_id),
                "facets": {"eduwork": {"organizationId": str(organization_id)}},
            },
            "job": {"namespace": "eduwork", "name": job_name, "facets": {}},
            "inputs": [{"namespace": "eduwork", "name": name, "facets": {}} for name in inputs],
            "outputs": [{"namespace": "eduwork", "name": name, "facets": {}} for name in outputs],
        }
        path = self.event_root / f"{run_id}-{event_type.lower()}.json"
        temporary = self.event_root / f".{path.name}.{uuid.uuid4().hex}.tmp"
        temporary.write_text(json.dumps(event, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)
        return path

    def trace(self, organization_id: uuid.UUID, node_id: uuid.UUID) -> LineageTrace:
        nodes = list(
            self.session.scalars(
                select(LineageNode).where(LineageNode.organization_id == organization_id)
            )
        )
        edges = list(
            self.session.scalars(
                select(LineageEdge).where(LineageEdge.organization_id == organization_id)
            )
        )
        relevant_ids = {node_id}
        changed = True
        while changed:
            changed = False
            for edge in edges:
                if edge.to_node_id in relevant_ids and edge.from_node_id not in relevant_ids:
                    relevant_ids.add(edge.from_node_id)
                    changed = True
                if edge.from_node_id in relevant_ids and edge.to_node_id not in relevant_ids:
                    relevant_ids.add(edge.to_node_id)
                    changed = True
        return LineageTrace(
            nodes=[
                {
                    "id": str(node.id),
                    "type": node.node_type,
                    "namespace": node.namespace,
                    "name": node.name,
                    "facets": node.facets_json,
                }
                for node in nodes
                if node.id in relevant_ids
            ],
            edges=[
                {
                    "id": str(edge.id),
                    "from": str(edge.from_node_id),
                    "to": str(edge.to_node_id),
                    "relation": edge.relation_type,
                    "field_mapping": edge.field_mapping_json,
                }
                for edge in edges
                if edge.from_node_id in relevant_ids and edge.to_node_id in relevant_ids
            ],
        )
