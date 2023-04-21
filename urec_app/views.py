from django.shortcuts import render, redirect
from django.http import HttpResponse, FileResponse, Http404
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .forms import *
from django.views.generic import ListView, TemplateView
from django.urls import reverse_lazy
from .storage_backends import *

import boto3

# Create your views here.

# Home Page
@login_required
def home(request):
    return render(request, 'urec_app/home.html')

# Accident Ticket Page
@login_required
def accident(request):
    return render(request, 'urec_app/accident.html')

# Create Accident Ticket
# def create_accident_ticket(request):
#     if request.method == "POST":
#         accident_ticket = Accident_Ticket_Form(request.POST)
#         injury_type = Accident_Ticket_Injury_Form(request.POST)
#         contact_info = Accident_Ticket_Contact_Info_Form(request.POST)
#         if accident_ticket.is_valid() and injury_type.is_valid() and contact_info.is_valid():
#             accident_instance = accident_ticket.save(commit=False)
#             injury_instance = injury_type.save(commit=False)
#             contact_instance = contact_info.save(commit=False)
#             accident_instance.save()
#             injury_instance.accident_ticket = accident_instance
#             injury_instance.save()
#             contact_instance.accident_ticket = accident_instance
#             contact_instance.save()
#
#             return redirect('accident')
#             # accident_ticket = Accident_Ticket_Form()
#             # injury_type = Accident_Ticket_Injury_Form()
#             # contact_info = Accident_Ticket_Contact_Info_Form()
#     else:
#         accident_ticket = Accident_Ticket_Form()
#         injury_type = Accident_Ticket_Injury_Form()
#         contact_info = Accident_Ticket_Contact_Info_Form()
#     context = { 'accident_ticket': accident_ticket, 'injury_type': injury_type, 'contact_info': contact_info}
#     return render(request, 'urec_app/create_accident_ticket.html', context)

class CreateAccidentTicket(TemplateView):
    template_name = "urec_app/create_accident_ticket.html"

    def get(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return redirect('http://127.0.0.1:8000/accounts/login')
        formset = AccidentTicketInjury(queryset=Accident_Ticket_Injury.objects.none())
        accident_ticket = Accident_Ticket_Form()
        patient = Accident_Ticket_Contact_Patient_Form()
        witness = Accident_Ticket_Contact_Witness_Form()
        context = {
            'accident_ticket': accident_ticket,
            'accident_ticket_injury_formset': formset,
            'patient': patient,
            'witness': witness,
        }
        return self.render_to_response(context)

    def post(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return redirect('http://127.0.0.1:8000/accounts/login')
        accident_ticket = Accident_Ticket_Form(data=self.request.POST)
        injury_type = AccidentTicketInjury(data=self.request.POST)
        patient = Accident_Ticket_Contact_Patient_Form(data=self.request.POST)
        witness = Accident_Ticket_Contact_Witness_Form(data=self.request.POST)

        if accident_ticket.is_valid() and injury_type.is_valid() and patient.is_valid() and witness.is_valid():
            accident_instance = accident_ticket.save(commit=False)
            injury_instance = injury_type.save(commit=False)
            patient_instance = patient.save(commit=False)
            witness_instance = witness.save(commit=False)
            accident_instance.save()
            for i in injury_instance:
                i.accident_ticket = accident_instance
                i.save()

            patient_instance.accident_ticket = accident_instance
            patient_instance.save()
            witness_instance.patient = patient_instance
            witness_instance.accident_ticket = accident_instance
            witness_instance.save()

            return redirect('home')

        return self.render_to_response({'accident-ticket-injury-formset': injury_type})


# View all Accident Tickets
@login_required
def view_accident_tickets(request):
    accident_ticket = Accident_Ticket.objects.all()
    injury_type = Accident_Ticket_Injury.objects.all()
    patient = Accident_Ticket_Contact_Patient.objects.all()

    context = {'accident_ticket': accident_ticket, 'injury_type': injury_type, 'contact_info': patient}
    return render(request, 'urec_app/view_accident_tickets.html', context)

# Counts Page
@login_required
def count(request):
    return render(request, 'urec_app/count.html')

# Update Count in Facilities
@login_required
def count_update(request):
    if request.method == 'POST':
        count_form = CountFormSet(request.POST)
        if count_form.is_valid():
            count_form.save()

            return redirect('count')
    count_form = CountFormSet(queryset=Count.objects.none())

    context = {'count_form': count_form}
    return render(request, 'urec_app/count_update.html', context)

# View All Count History
@login_required
def count_view_history(request):
    count_item = Count.objects.all()
    context = {'count_item': count_item}
    return render(request, 'urec_app/count_view_history.html', context)

# ERP Page
@login_required
def erp(request):
    return render(request, 'urec_app/erp.html')

@login_required
def create_erp(request):
    if request.method == "POST":
        # get form data from requests
        erp_file = ERP_Upload_Form(request.POST, request.FILES)
        erp_obj = ERP_Form(request.POST)

        # extract file information
        uploadfile = request.FILES['file']  # entire file
        filelocation = uploadfile.name  # file name from entire file
        if erp_file.is_valid() and erp_obj.is_valid():
            # make instance of model with files information, then save to database
            erp = Erp(title = request.POST['title'], filename = filelocation, description = request.POST['description'])
            erp.save()

            # make instance of media storage, then save the file
            mediastorage = PublicMediaStorage()
            mediastorage.save(filelocation, uploadfile)
            
            # return user to erp home
            return redirect('erp')
    else:
        # give blank forms if not POST request
        erp_file = ERP_Upload_Form()
        erp_obj = ERP_Form()
    context = {'erp_obj': erp_obj, 'erp_file': erp_file}
    return render(request, 'urec_app/create_erp.html', context)

@login_required
def delete_erp(request, filename):
    erp = Erp.objects.get(filename=filename)
    if request.method == "POST":
        # delete from database
        erp.delete()
        # set variables necessary for S3 connection
        AWS_REGION = settings.AWS_DEFAULT_REGION
        S3_BUCKET_NAME = settings.AWS_STORAGE_BUCKET_NAME
        ACCESS_ID = settings.AWS_ACCESS_KEY_ID
        ACCESS_KEY = settings.AWS_SECRET_ACCESS_KEY
        # initialize S3 connections
        s3_resource = boto3.resource("s3", aws_access_key_id=ACCESS_ID,
         aws_secret_access_key= ACCESS_KEY, region_name=AWS_REGION)
        # get instance of S3 object based on filename
        s3_object = s3_resource.Object(S3_BUCKET_NAME, 'erpfiles/' + str(filename))
        # delete S3 object
        s3_object.delete()

    return redirect('view_erps')

@login_required
def download_erp(request, filename):
    # set variables necessary for S3 connection
    AWS_REGION = settings.AWS_DEFAULT_REGION
    S3_BUCKET_NAME = settings.AWS_STORAGE_BUCKET_NAME
    ACCESS_ID = settings.AWS_ACCESS_KEY_ID
    ACCESS_KEY = settings.AWS_SECRET_ACCESS_KEY
    # initialize S3 connection
    s3_client = boto3.client("s3", aws_access_key_id=ACCESS_ID,
         aws_secret_access_key= ACCESS_KEY, region_name=AWS_REGION)
    # download object in user's browser
    # s3_client.download_file(S3_BUCKET_NAME, str(filename), 'erpfiles/' + str(filename))
    erp_url = s3_client.generate_presigned_url('get_object',
        Params={'Bucket': S3_BUCKET_NAME, 'Key': 'erpfiles/' + str(filename)},
        ExpiresIn=300)
        
    context = {"erp_url": erp_url , "filename": filename}
    return render(request, 'urec_app/download_erp.html', context)


@login_required
def view_erps(request):
    Erps = Erp.objects.all()
    context = {"Erps": Erps}
    return render(request, 'urec_app/view_erps.html', context)

@login_required
def form(request):
    return render(request, 'urec_app/form.html')

# Incident Ticket Page
@login_required
def incident(request):
    return render(request, 'urec_app/incident.html')

# Create Incident Ticket
# def create_incident_ticket(request):
#     if request.method == "POST":
#         incident_ticket = Incident_Ticket_Form(request.POST)
#         incident_type = Incident_Ticket_Incident_Form(request.POST)
#         contact_info = Incident_Ticket_Contact_Info_Form(request.POST)
#         if incident_ticket.is_valid() and incident_type.is_valid() and contact_info.is_valid():
#             incident_instance = incident_ticket.save(commit=False)
#             incident_type_instance = incident_type.save(commit=False)
#             contact_instance = contact_info.save(commit=False)
#             incident_instance.save()
#             incident_type_instance.incident_ticket = incident_instance
#             incident_type_instance.save()
#             contact_instance.incident_ticket = incident_instance
#             contact_instance.save()
#
#             return redirect('incident')
#             # incident_ticket = Incident_Ticket_Form()
#             # incident_type = Incident_Ticket_Incident_Form()
#             # contact_info = Incident_Ticket_Contact_Info_Form()
#     else:
#         incident_ticket = Incident_Ticket_Form()
#         incident_type = Incident_Ticket_Incident_Form()
#         contact_info = Incident_Ticket_Contact_Info_Form()
#     context = { 'incident_ticket': incident_ticket, 'incident_type': incident_type, 'contact_info': contact_info}
#     return render(request, 'urec_app/create_incident_ticket.html', context)


class CreateIncidentTicket(TemplateView):
    template_name = "urec_app/create_incident_ticket.html"
    def get(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return redirect('http://127.0.0.1:8000/accounts/login')
        formset = IncidentTicketIncidentForm(queryset=Incident_Ticket_Incident.objects.none())
        incident_ticket = Incident_Ticket_Form()
        patient_contact = Incident_Ticket_Contact_Patient_Form()
        witness_contact = Incident_Ticket_Contact_Witness_Form()

        context = {
            'incident_ticket': incident_ticket,
            'incident_type_formset': formset,
            'patient_contact': patient_contact,
            'witness_contact': witness_contact,
        }
        return self.render_to_response(context)

    def post(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return redirect('http://127.0.0.1:8000/accounts/login')
        incident_ticket = Incident_Ticket_Form(data=self.request.POST)
        incident_type = IncidentTicketIncidentForm(data=self.request.POST)
        patient_contact = Incident_Ticket_Contact_Patient_Form(data=self.request.POST)
        witness_contact = Incident_Ticket_Contact_Witness_Form(data=self.request.POST)

        if incident_ticket.is_valid() and incident_type.is_valid() \
                and patient_contact.is_valid() and witness_contact.is_valid():

            ticket_instance = incident_ticket.save(commit=False)
            type_instance = incident_type.save(commit=False)
            patient_instance = patient_contact.save(commit=False)
            witness_instance = witness_contact.save(commit=False)
            ticket_instance.save()
            for i in type_instance:
                i.incident_ticket = ticket_instance
                i.save()

            patient_instance.incident_ticket = ticket_instance
            patient_instance.save()
            witness_instance.incident_ticket = ticket_instance
            witness_instance.patient = patient_instance
            witness_instance.save()

            return redirect('home')

        return self.render_to_response({'incident_type_formset': incident_type})


# View all Incident Tickets
@login_required
def view_incident_tickets(request):
    incident_ticket = Incident_Ticket.objects.all()
    incident_type = Incident_Ticket_Incident.objects.all()
    patient_contact = Incident_Ticket_Contact_Patient.objects.all()

    context = {'incident_ticket': incident_ticket, 'incident_type': incident_type, 'patient_contact': patient_contact}
    return render(request, 'urec_app/view_incident_tickets.html', context)

@login_required
def sop(request):
    return render(request, 'urec_app/sop.html')

# Task Page
@login_required
def task(request):
    return render(request, 'urec_app/task.html')

# Create New Task
@login_required
def create_task(request):
    if request.method == "POST":
        task_obj = Task_Form(request.POST)
        if task_obj.is_valid():
            task_obj.pk = None
            task_obj.save()
        # task_obj = Task_Form(request.POST)
        # if task_obj.is_valid():
        #     task_obj.pk = None
        #     task_obj.save()
        # task_obj = Task_Form(request.POST)
        # if task_obj.is_valid():
        #     task_obj.pk = None
        #     task_obj.save()

            return redirect('task')
    else:
        task_obj = Task_Form()
    context = {'task_obj': task_obj}
    return render(request, 'urec_app/create_task.html', context)

# View All Created Tasks reguardless of completion
@login_required
def all_tasks(request):
    task_item = Task.objects.all()

    context = {'task_item': task_item}
    return render(request, 'urec_app/all_tasks.html', context)

@login_required
def survey(request):
    return render(request, 'urec_app/survey.html')
