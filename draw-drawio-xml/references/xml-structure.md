# Draw.io XML Structure

Use this reference when hand-writing XML fragments, checking generated output, or debugging diagrams.net import failures.

## Minimal File Shape

```xml
<mxfile host="app.diagrams.net">
  <diagram id="diagram_id" name="Architecture">
    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" page="1" pageWidth="1169" pageHeight="827">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

## Vertex Cell

```xml
<mxCell id="service_a" value="Service A" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="1">
  <mxGeometry x="80" y="80" width="170" height="70" as="geometry"/>
</mxCell>
```

## Edge Cell

```xml
<mxCell id="edge_1" value="RPC" style="rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;endFill=1;strokeColor=#666666;" edge="1" parent="1" source="service_a" target="service_b">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

## Dashed Edge

```xml
<mxCell id="edge_config" value="config" style="rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;endFill=1;strokeColor=#666666;dashed=1;" edge="1" parent="1" source="config_a" target="service_b">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```
