import phonenumbers
from django import forms
from .models import Reserva, DiaFeriado, Coupon
from datetime import date, datetime, timedelta
from django.core.exceptions import ValidationError
from dns import resolver

class ReservaForm(forms.ModelForm):
    coupon_code = forms.CharField(max_length=50, required=False, label="Código de Cupón", help_text="Opcional")
    class Meta:
        model = Reserva
        fields = ['nombre', 'correo', 'telefono', 'direccion', 'fecha', 'dias', 'espacio_techado']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'correo': forms.EmailInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'telefono': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'direccion': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'espacio_techado': forms.RadioSelect(choices=[(True, 'Sí'), (False, 'No')]),
        }
    
    def clean_coupon_code(self):
        code = self.cleaned_data.get('coupon_code')
        if code:
            try:
                coupon = Coupon.objects.get(code=code)
                if not coupon.is_valid():
                    raise ValidationError("El cupón no es válido o ha expirado.")
                return coupon # Return the coupon object, not just the code
            except Coupon.DoesNotExist:
                raise ValidationError("El código de cupón no existe.")
        return None # Return None if no code was entered

    def clean_fecha(self):
        fecha = self.cleaned_data.get('fecha')
        if not fecha:
            # Si no hay fecha, la validación de campo requerido se encargará.
            return fecha

        today = date.today()
        now = datetime.now()

        # 1. No se puede reservar para hoy ni para fechas pasadas (para reservas nuevas).
        if fecha <= today:
            if not self.instance.pk:  # Solo para reservas nuevas
                raise forms.ValidationError("No puedes reservar para hoy ni para fechas pasadas.")

        # 2. No se puede reservar en un día festivo.
        if DiaFeriado.objects.filter(fecha=fecha).exists():
            # Permite guardar si la reserva ya estaba en ese día festivo (en caso de que se agregara después).
            if not (self.instance.pk and self.instance.fecha == fecha):
                raise forms.ValidationError("La fecha seleccionada es un día festivo. Por favor, elige otra.")

        # 3. No se puede reservar para el día siguiente después de las 20:00.
        if fecha == today + timedelta(days=1) and now.hour >= 20:
            if not (self.instance.pk and self.instance.fecha == fecha):
                raise forms.ValidationError("No se puede reservar para mañana después de las 20:00.")

        # 4. Límite de 3 reservas por día.
        # Excluimos la instancia actual del conteo si estamos editando.
        qs = Reserva.objects.filter(fecha=fecha)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.count() >= 3:
            raise forms.ValidationError("Ya se alcanzó el máximo de 3 reservas para este día.")

        return fecha