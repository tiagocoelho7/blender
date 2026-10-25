# SPDX-License-Identifier: GPL-3.0-or-later

bl_info = {
    "name": "Tiago Tools",
    "author": "Tiago Coelho",
    "version": (1, 0, 2),
    "blender": (5, 0, 0),
    "location": "View3D > Sidebar > Tiago",
    "description": "Ferramentas pessoais para desativar modifiers e criar Safe Sub",
    "category": "Object",
}

import bpy
from bpy.props import EnumProperty
from bpy.types import Operator, Panel


# -----------------------------------------------------------------------------
# Utilitarios
# -----------------------------------------------------------------------------


def _collect_objects_from_visible_collections(layer_collection, result):
    """Coleta objetos ligados a collections efetivamente visiveis no View Layer."""
    if not layer_collection.is_visible:
        return

    for obj in layer_collection.collection.objects:
        result.add(obj)

    for child in layer_collection.children:
        _collect_objects_from_visible_collections(child, result)


# -----------------------------------------------------------------------------
# 1) Desativar Modifiers
# -----------------------------------------------------------------------------


class TIAGO_OT_disable_modifiers(Operator):
    bl_idname = "tiago.disable_modifiers"
    bl_label = "Desativar Modifiers"
    bl_description = "Desativa modifiers no viewport sem alterar o estado das collections"
    bl_options = {'REGISTER', 'UNDO'}

    scope: EnumProperty(
        name="Escopo",
        items=(
            ('ALL', "Todos", "Todos os objetos da Scene, inclusive collections ocultas/desativadas"),
            ('VISIBLE_COLLECTIONS', "Collections visiveis", "Somente objetos ligados a collections visiveis no View Layer atual"),
        ),
        default='ALL',
    )

    def execute(self, context):
        scene = context.scene
        view_layer = context.view_layer

        if scene is None or view_layer is None:
            self.report({'ERROR'}, "Nenhuma Scene/View Layer ativa")
            return {'CANCELLED'}

        if self.scope == 'ALL':
            objects = list(scene.objects)
            mode_label = "todos os objetos"
        else:
            object_set = set()
            _collect_objects_from_visible_collections(view_layer.layer_collection, object_set)
            objects = list(object_set)
            mode_label = "collections visiveis"

        objects_with_modifiers = 0
        modifiers_found = 0
        changed = 0
        already_disabled = 0
        errors = 0

        for obj in objects:
            try:
                modifiers = list(obj.modifiers)
            except Exception as exc:
                errors += 1
                print(f'[Tiago Tools] ERRO ao ler modifiers de "{obj.name}": {exc}')
                continue

            if not modifiers:
                continue

            objects_with_modifiers += 1

            for modifier in modifiers:
                modifiers_found += 1
                try:
                    if modifier.show_viewport:
                        modifier.show_viewport = False
                        changed += 1
                    else:
                        already_disabled += 1
                except Exception as exc:
                    errors += 1
                    print(
                        f'[Tiago Tools] ERRO em "{obj.name}" > '
                        f'"{modifier.name}": {exc}'
                    )

        message = (
            f"{changed} desativado(s); {already_disabled} ja estavam desativados "
            f"({mode_label})"
        )
        if errors:
            message += f"; {errors} erro(s) - veja o Console"
            self.report({'WARNING'}, message)
        else:
            self.report({'INFO'}, message)

        print()
        print("=" * 60)
        print("TIAGO TOOLS - MODIFIERS DESATIVADOS")
        print("=" * 60)
        print(f"Modo: {mode_label}")
        print(f"Objetos encontrados: {len(objects)}")
        print(f"Objetos com modifiers: {objects_with_modifiers}")
        print(f"Modifiers encontrados: {modifiers_found}")
        print(f"Desativados agora: {changed}")
        print(f"Ja desativados: {already_disabled}")
        print(f"Erros: {errors}")
        print("=" * 60)

        return {'FINISHED'}


# -----------------------------------------------------------------------------
# 2) Safe Sub
# -----------------------------------------------------------------------------


class TIAGO_OT_safe_add_subdivision(Operator):
    bl_idname = "tiago.safe_add_subdivision"
    bl_label = "Adicionar Subdivision desativado"
    bl_description = (
        "Adiciona Subdivision Surface com viewport e render desligados "
        "e niveis 0 para reduzir o risco de avaliacao pesada"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        modifier = None

        try:
            # A API cria o modifier primeiro; desligamos imediatamente, antes de
            # devolver o controle ao Blender/viewport.
            modifier = obj.modifiers.new(name="Subdivision", type='SUBSURF')
            modifier.show_viewport = False
            modifier.show_render = False
            modifier.levels = 0
            modifier.render_levels = 0
            modifier.show_in_editmode = False
            modifier.show_on_cage = False
        except Exception as exc:
            if modifier is None:
                # A criacao falhou sem retornar um modifier para remover.
                self.report({'ERROR'}, f"Nao foi possivel criar Subdivision: {exc}")
                return {'CANCELLED'}

            try:
                # Remover somente o modifier criado nesta chamada.
                obj.modifiers.remove(modifier)
            except Exception as cleanup_exc:
                # Blender nao cria etapa de Undo quando retornamos CANCELLED.
                # Se a limpeza falhou, FINISHED permite o Undo do operador.
                print(
                    f'[Tiago Tools] Safe Sub: erro de configuracao: {exc}; '
                    f'erro ao remover modifier novo: {cleanup_exc}'
                )
                self.report(
                    {'WARNING'},
                    'Falha no Safe Sub e na limpeza; confira os modifiers e use Undo (Ctrl+Z)'
                )
                return {'FINISHED'}

            self.report(
                {'ERROR'},
                f'Nao foi possivel configurar Subdivision: {exc} (novo modifier removido)'
            )
            return {'CANCELLED'}

        self.report(
            {'INFO'},
            f'Subdivision desativado adicionado a "{obj.name}"'
        )
        return {'FINISHED'}


# -----------------------------------------------------------------------------
# Painel
# -----------------------------------------------------------------------------


class VIEW3D_PT_tiago_tools(Panel):
    bl_label = "Tiago Tools"
    bl_idname = "VIEW3D_PT_tiago_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tiago"

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="Modifiers", icon='MODIFIER')

        row = box.row(align=True)
        op = row.operator(
            TIAGO_OT_disable_modifiers.bl_idname,
            text="Todos",
        )
        op.scope = 'ALL'

        op = row.operator(
            TIAGO_OT_disable_modifiers.bl_idname,
            text="Visiveis",
        )
        op.scope = 'VISIBLE_COLLECTIONS'

        box = layout.box()
        box.label(text="Subdivision", icon='MOD_SUBSURF')
        box.operator(
            TIAGO_OT_safe_add_subdivision.bl_idname,
            text="Adicionar desativado",
            icon='MOD_SUBSURF',
        )

CLASSES = (
    TIAGO_OT_disable_modifiers,
    TIAGO_OT_safe_add_subdivision,
    VIEW3D_PT_tiago_tools,
)


# Acompanhar somente classes efetivamente registradas por este modulo.
# Em caso de falha parcial, o proximo unregister() pode tentar limpar o restante.
_REGISTERED_CLASSES = []


def register():
    registered_now = []
    try:
        for cls in CLASSES:
            if cls in _REGISTERED_CLASSES:
                continue
            bpy.utils.register_class(cls)
            _REGISTERED_CLASSES.append(cls)
            registered_now.append(cls)
    except Exception:
        # Desfazer apenas os registros novos desta tentativa, na ordem inversa.
        for cls in reversed(registered_now):
            try:
                bpy.utils.unregister_class(cls)
            except Exception as cleanup_exc:
                print(
                    f'[Tiago Tools] Erro ao reverter registro de {cls.__name__}: '
                    f'{cleanup_exc}'
                )
            else:
                _REGISTERED_CLASSES.remove(cls)
        raise


def unregister():
    first_error = None
    for cls in reversed(CLASSES):
        if cls not in _REGISTERED_CLASSES:
            continue
        try:
            bpy.utils.unregister_class(cls)
        except Exception as exc:
            if first_error is None:
                first_error = exc
            print(f'[Tiago Tools] Erro ao desregistrar {cls.__name__}: {exc}')
        else:
            _REGISTERED_CLASSES.remove(cls)

    if first_error is not None:
        pending = ', '.join(cls.__name__ for cls in _REGISTERED_CLASSES)
        raise RuntimeError(
            f'Tiago Tools: classes ainda registradas ({pending}); tente unregister() novamente'
        ) from first_error
