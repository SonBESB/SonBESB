# Prueba manual: registro del CustomScript (`PLANTREGISTERCUSTOMSCRIPTS`)

**Este documento describe un procedimiento manual que un humano ejecuta
en una máquina Windows real con AutoCAD Plant 3D instalado.** Ningún paso
de este documento se automatiza desde este repositorio — no existe
código aquí que abra AutoCAD, ejecute comandos de la línea de comandos de
Plant 3D, o modifique archivos de Plant 3D directamente.

## Prerrequisito

Haber generado el paquete de despliegue (botón "Generar paquete Plant 3D"
en la UI, o `plant3d/deployment/package_builder.build_deployment_package`)
y tener `HDPE_SEGMENTED_ELBOW.py` disponible. Ver
`docs/PLANT3D_CUSTOMSCRIPT.md` para qué contiene ese archivo y qué NO
contiene (es un scaffold, no una implementación completa — se espera que
la compilación falle o el resultado no sea funcional hasta completar la
sección de geometría/puertos con la API real).

## Checklist

- [ ] **1. Ubicar el Shared Content Folder real** de la instalación de
      Plant 3D. Ejecutar `plant3d/environment/detector.py` en esa máquina
      (o completar `plant3d_config.yaml` a mano) — ver
      `docs/PLANT3D_ENVIRONMENT.md`.
- [ ] **2. Copiar el archivo** `HDPE_SEGMENTED_ELBOW.py` a:
      ```
      <Shared Content Folder>\CPak Common\CustomScripts\
      ```
- [ ] **3. Abrir AutoCAD Plant 3D** con el toolset Plant 3D activo.
- [ ] **4. Ejecutar el comando** `PLANTREGISTERCUSTOMSCRIPTS` en la línea
      de comandos.
- [ ] **5. Observar el resultado.** Dos posibilidades:
      - **Falla de compilación**: Plant 3D reporta un error en la línea
        de comandos (se espera, dado que la sección de geometría es un
        marcador `NOT_VERIFIED_AGAINST_REAL_PLANT3D_API`). Copiar el
        texto completo del error.
      - **Compila sin error**: registrar exactamente qué apareció (el
        nombre bajo qué grupo, en qué panel).
- [ ] **6. Copiar el resultado completo** (éxito o error) a
      `plant3d_validation/registration_result.txt`. Este archivo debe
      dejar de estar vacío — mientras esté vacío,
      `plant3d/deployment/manifest.py` no avanza el estado más allá de
      `GENERATED` (ver `plant3d_validation/README.md`).
- [ ] **7. (Opcional) Adjuntar capturas de pantalla** en
      `plant3d_validation/screenshots/`.

## Qué NO hacer

- No editar manualmente `validation_manifest.json` para marcar
  `REGISTERED` — ese archivo se deriva automáticamente de la existencia y
  contenido de `registration_result.txt` (ver
  `plant3d/deployment/manifest.py::update_manifest_with_evidence`).
- No "arreglar" el script a mano solo para que compile sin antes
  confirmar la API real que reemplaza al marcador — cualquier cambio al
  generador debe pasar por `plant3d/generators/custom_script_generator.py`
  con una fuente citable (ver `docs/PLANT3D_CUSTOMSCRIPT.md`), no un
  parche puntual en el `.py` ya generado.

## Siguiente paso

Con `registration_result.txt` completo, continuar con
`docs/PLANT3D_CATALOG_WORKFLOW.md`.
