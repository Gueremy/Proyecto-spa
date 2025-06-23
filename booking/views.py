from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from .forms import ReservaForm
from .models import Reserva, DiaFeriado, Coupon
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.db.models import Count
from datetime import datetime, timedelta, date
from django.contrib.admin.views.decorators import staff_member_required
import json
import openpyxl
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

def login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_panel')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None and user.is_staff:
                login(request, user)
                return redirect('admin_panel')
            else:
                messages.error(request, "Acceso denegado. Solo para administradores.")
        else:
            messages.error(request, "Nombre de usuario o contraseña inválidos.")
    else:
        form = AuthenticationForm()
    return render(request, 'booking/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('reservation_form')

@staff_member_required
def admin_panel(request):
    reservas = Reserva.objects.all()

    # Aplicar filtros desde la URL (GET)
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    pagado = request.GET.get('pagado')

    if fecha_desde:
        reservas = reservas.filter(fecha__gte=fecha_desde)
    if fecha_hasta:
        reservas = reservas.filter(fecha__lte=fecha_hasta)
    if pagado in ['true', 'false']:
        reservas = reservas.filter(pagado=(pagado == 'true'))

    reservas = reservas.order_by('-fecha')

    dias_feriados = DiaFeriado.objects.all().order_by('fecha')
    coupons = Coupon.objects.all().order_by('-valid_to') # Get all coupons
    return render(request, 'booking/admin_panel.html', {
        'reservas': reservas,
        'dias_feriados': dias_feriados,
        'coupons': coupons, # Pass coupons to the template
        'request': request, # Pasamos el request para acceder a los filtros en la plantilla
    })

@staff_member_required
def editar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    if request.method == 'POST':
        form = ReservaForm(request.POST, instance=reserva)
        if form.is_valid():
            form.save()
            return redirect('admin_panel')
    else:
        form = ReservaForm(instance=reserva)
    return render(request, 'booking/editar_reserva.html', {'form': form, 'reserva': reserva})

@staff_member_required
def eliminar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    if request.method == 'POST':
        reserva.delete()
        return redirect('admin_panel')
    return render(request, 'booking/eliminar_reserva.html', {'reserva': reserva})

def reservation_form(request):
    if request.method == 'POST':
        form = ReservaForm(request.POST)
        if form.is_valid():
            # Assign the validated coupon object to the instance before saving
            if 'coupon_code' in form.cleaned_data and form.cleaned_data['coupon_code']:
                form.instance.coupon = form.cleaned_data['coupon_code']

            reserva = form.save()
            # Enviar correo de confirmación usando plantillas HTML y de texto
            subject = '¡Tu reserva en Spa Confort ha sido confirmada!'
            context = {'reserva': reserva}

            html_message = render_to_string('booking/email/reservation_confirmation.html', context)
            plain_message = render_to_string('booking/email/reservation_confirmation.txt', context)

            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[reserva.correo],
                fail_silently=False,
                html_message=html_message,
            )
            return redirect('reservation_success', reserva_id=reserva.id)
        # Si el formulario no es válido, se renderizará de nuevo con los errores.
    else:
        form = ReservaForm()

    # --- Contexto para la validación del lado del cliente (JavaScript) ---
    # Esto mejora la experiencia del usuario, pero la validación final y segura
    # se realiza en el servidor a través del formulario.
    hoy = date.today()
    ahora = datetime.now()

    if ahora.hour >= 20:
        min_fecha = hoy + timedelta(days=2)
    else:
        min_fecha = hoy + timedelta(days=1)

    return render(request, 'booking/reservation_form.html', {
        'form': form,
        'min_fecha': min_fecha.isoformat(),
        'fechas_bloqueadas': json.dumps([
            f.strftime('%Y-%m-%d') for f in Reserva.objects.values('fecha')
            .annotate(count=Count('id'))
            .filter(count__gte=3)
            .values_list('fecha', flat=True)
        ]),
        'dias_festivos': json.dumps([
            d.strftime('%Y-%m-%d') for d in DiaFeriado.objects.values_list('fecha', flat=True)
        ]),
    })
def reservation_success(request, reserva_id):
    reserva = Reserva.objects.get(id=reserva_id)
    return render(request, 'booking/reservation_success.html', {'reserva': reserva})
@staff_member_required
def agregar_feriado(request):
    if request.method == 'POST':
        fecha = request.POST.get('fecha')
        descripcion = request.POST.get('descripcion', '')
        if fecha:
            DiaFeriado.objects.get_or_create(fecha=fecha, defaults={'descripcion': descripcion})
    return redirect('admin_panel')

@staff_member_required
def eliminar_feriado(request, feriado_id):
    if request.method == 'POST':
        DiaFeriado.objects.filter(id=feriado_id).delete()
    return redirect('admin_panel')

@staff_member_required
def agregar_cupon(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        discount_percentage = request.POST.get('discount_percentage')
        valid_from = request.POST.get('valid_from')
        valid_to = request.POST.get('valid_to')

        if code and discount_percentage and valid_from and valid_to:
            try:
                Coupon.objects.create(
                    code=code,
                    discount_percentage=int(discount_percentage),
                    valid_from=valid_from,
                    valid_to=valid_to
                )
            except Exception as e:
                messages.error(request, f"Error al agregar cupón: {e}")
    return redirect('admin_panel')

@staff_member_required
def eliminar_cupon(request, coupon_id):
    if request.method == 'POST':
        Coupon.objects.filter(id=coupon_id).delete()
    return redirect('admin_panel')
@staff_member_required
def export_reservas_excel(request):
    """
    Genera un archivo Excel con las reservas.
    - Si es POST, exporta las reservas seleccionadas.
    - Si es GET, exporta las reservas filtradas.
    """
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_ids')
        if not selected_ids:
            messages.error(request, "No seleccionaste ninguna reserva para exportar.")
            return redirect('admin_panel')
        reservas = Reserva.objects.filter(id__in=selected_ids).order_by('-fecha')
    else: # GET
        reservas = Reserva.objects.all()
        fecha_desde = request.GET.get('fecha_desde')
        fecha_hasta = request.GET.get('fecha_hasta')
        pagado = request.GET.get('pagado')

        if fecha_desde:
            reservas = reservas.filter(fecha__gte=fecha_desde)
        if fecha_hasta:
            reservas = reservas.filter(fecha__lte=fecha_hasta)
        if pagado in ['true', 'false']:
            reservas = reservas.filter(pagado=(pagado == 'true'))
        reservas = reservas.order_by('-fecha')
    
    # Crear un libro de trabajo y una hoja
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = 'Reservas'

    # Escribir la cabecera
    headers = ['N° Reserva', 'Nombre Cliente', 'Fecha', 'Días', 'Total', 'Pagado', 'Espacio Techado', 'Correo', 'Teléfono']
    sheet.append(headers)

    # Escribir los datos de cada reserva
    for reserva in reservas:
        sheet.append([
            reserva.numero_reserva,
            reserva.nombre,
            reserva.fecha,
            reserva.dias,
            reserva.total,
            'Sí' if reserva.pagado else 'No',
            'Sí' if reserva.espacio_techado else 'No',
            reserva.correo,
            reserva.telefono,
        ])

    # Crear la respuesta HTTP
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=reservas.xlsx'
    workbook.save(response)
    
    return response

@staff_member_required
def export_reservas_pdf(request):
    """
    Genera un archivo PDF con una tabla de las reservas.
    - Si es POST, exporta las reservas seleccionadas.
    - Si es GET, exporta las reservas filtradas.
    """
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_ids')
        if not selected_ids:
            messages.error(request, "No seleccionaste ninguna reserva para exportar.")
            return redirect('admin_panel')
        reservas = Reserva.objects.filter(id__in=selected_ids).order_by('-fecha')
    else: # GET
        reservas = Reserva.objects.all()
        fecha_desde = request.GET.get('fecha_desde')
        fecha_hasta = request.GET.get('fecha_hasta')
        pagado = request.GET.get('pagado')

        if fecha_desde:
            reservas = reservas.filter(fecha__gte=fecha_desde)
        if fecha_hasta:
            reservas = reservas.filter(fecha__lte=fecha_hasta)
        if pagado in ['true', 'false']:
            reservas = reservas.filter(pagado=(pagado == 'true'))
        reservas = reservas.order_by('-fecha')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reservas.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Título del documento
    title = Paragraph("Reporte de Reservas", styles['h1'])
    elements.append(title)

    # Datos para la tabla
    data = [['N° Reserva', 'Cliente', 'Fecha', 'Total', 'Pagado']]
    for reserva in reservas:
        data.append([
            reserva.numero_reserva,
            reserva.nombre,
            reserva.fecha.strftime('%d-%m-%Y'),
            f"${reserva.total:,.0f}".replace(",", "."),
            'Sí' if reserva.pagado else 'No'
        ])

    # Crear y estilizar la tabla
    table = Table(data, colWidths=[1.2*inch, 2*inch, 1.2*inch, 1.2*inch, 0.8*inch])
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    table.setStyle(style)
    elements.append(table)

    doc.build(elements)
    return response