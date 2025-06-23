from django.contrib import admin
from django.utils.html import format_html
from django.contrib.humanize.templatetags.humanize import intcomma
from import_export.admin import ImportExportModelAdmin
from .models import Reserva, DiaFeriado, Coupon

@admin.register(Reserva)
class ReservaAdmin(ImportExportModelAdmin):
    """
    Configuración avanzada para el modelo Reserva en el panel de administración.
    """
    list_display = (
        'numero_reserva',
        'nombre',
        'fecha',
        'total_formatted',
        'pagado',
        'espacio_techado_icon'
    )
    list_filter = ('fecha', 'pagado', 'espacio_techado')
    search_fields = ('nombre', 'numero_reserva')
    date_hierarchy = 'fecha'
    ordering = ('-fecha',)

    @admin.display(description='Total', ordering='total')
    def total_formatted(self, obj):
        """Formatea el total como moneda chilena."""
        return f"${intcomma(int(obj.total))}"

    @admin.display(description='Espacio Techado', boolean=True)
    def espacio_techado_icon(self, obj):
        """Muestra un ícono de 'sí' o 'no' para el espacio techado."""
        return obj.espacio_techado

# Personalización global del sitio de administración
admin.site.site_header = "Panel de Reservas Spa Inflable"
admin.site.site_title = "Admin Spa Inflable"
admin.site.index_title = "Gestión de Reservas"

@admin.register(DiaFeriado)
class DiaFeriadoAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'descripcion')
    ordering = ('fecha',)

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percentage', 'is_active', 'valid_from', 'valid_to')
    list_filter = ('is_active',)
    search_fields = ('code',)