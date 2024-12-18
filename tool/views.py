from django.shortcuts import render, redirect
from tool.SensitivityTool.Sensitivity import analyzer
import time
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from pathlib import Path
import os
import subprocess
import shutil
from django.contrib.auth.decorators import login_required
from zipfile import ZipFile
from django.contrib.auth import authenticate, login, logout
import pandas as pd
import zipfile
from django.core.files import File
from .models import *
from .helpers.utils import *
from datetime import datetime


# @login_required(login_url='login')
def index(request):
    messages = []
    return render(request, "tool/home.html")

# @login_required(login_url='login')
def git_process(request):
    messages = []
    if request.method == 'POST':
        # print(request.POST.get("GitHub_repo"))
        if request.POST.get("GitHub_repo"):
            # time.sleep(1000)
            try:
                
                # Getting Start time
                start_time = datetime.now()

                output = ''

                print(request.POST.get("GitHub_repo"))
                BASE_DIR = Path(__file__).resolve().parent
                WORKING_DIR = os.path.join(BASE_DIR, "SensitivityTool", 'projects')
                if not os.path.exists(WORKING_DIR):
                    os.makedirs(WORKING_DIR)
                os.chdir(WORKING_DIR)
                
                # # Get repo URL 
                repo_url = request.POST.get("GitHub_repo")
                print("Original Repo URL: ",repo_url)
                if  repo_url.endswith('.git'):
                    repo_url = repo_url[:-4]
                print("CLeaned Repo URL: ", repo_url)
                
                projectID = repo_url.rsplit('/', 1)[1]+ "-"+ str(int(time.time() * 1000))
                project_path =  os.path.join(WORKING_DIR, repo_url.rsplit('/', 1)[1])
                # print(1,project_path)
                
                try:
                    subprocess.check_output(['git', 'clone', repo_url])
                except subprocess.CalledProcessError as e:
                    print('Cloning failed:', e)
                    # message.append(f'Cloning failed: {e}')
                    messages.append(f'Cloning failed please make sure the repository exists, and is publicly available.')
                    print(project_path)
                    if os.path.exists(project_path):
                        shutil.rmtree(project_path)
                    context = {'messages':messages}
                    return render(request, "tool/home.html",context=context)
                
                os.chdir(os.path.join(BASE_DIR, "SensitivityTool"))
                # try:
                #call the backend function
                output = analyzer(project_path, projectID)
                # except Exception as e:
                #     print(e)

                print(output)

                files_to_zip = []
                for root, dirs, files in os.walk(output):
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        relative_path = os.path.relpath(file_path, output)
                        files_to_zip.append((relative_path, open(file_path, 'rb').read()))

                # Create a temporary zip file
                zip_file_path = f'output/{projectID}.zip'  
                print(zip_file_path)
                with zipfile.ZipFile(zip_file_path, 'w') as zip_file:
                    for file_name, file_content in files_to_zip:
                        zip_file.writestr(file_name, file_content)
                
                if request.user.is_authenticated:
                    username = request.user
                else:
                    username = None
                
                obj= Job.objects.create(
                                    user=username, 
                                    name= f'{project_path.split("/")[-1]}.zip'
                                )
                with open(zip_file_path,mode="rb") as f:
                    obj.result = File(f, name=f'{projectID}.zip')
                    obj.save()
                


                # Bar Chart
                df = pd.read_csv(os.path.join(output,"Sorted Normalized Type Statistic.csv"))

                # Find all rows where the "SENSITIVITY LEVEL" column has non-zero values
                non_zero_sensitivity_rows = df[df['SENSITIVITY LEVEL'] != 0].head(30)

                # Extract class names and sensitivity levels
                class_names = non_zero_sensitivity_rows['CLASS NAME'].tolist()
                sensitivity_levels = non_zero_sensitivity_rows['SENSITIVITY LEVEL'].tolist()


                data = {
                    'class_names': class_names,
                    'sensitivity_levels': sensitivity_levels,
                }

                # Getting End time
                end_time = datetime.now()

                # Calculate and print the time difference
                execution_time = time_difference(start_time, end_time)

            except Exception as e:
                print(e)
                messages.append(f"Error: {e}")
                context = {'messages':messages}
                return render(request, "tool/home.html",context=context)
            finally:
                # #Check prject and delete it at the end
                if os.path.exists(project_path):
                    try:
                        shutil.rmtree(project_path)
                    except Exception as e:
                        print(e)
                
                if os.path.exists(output):
                    try:
                        shutil.rmtree(output)
                    except Exception as e:
                        print(e)
        
        # Go to results page
            return render(request, "tool/results.html", context={'data': data, 'zip': obj, 'time': execution_time})

        else:
            messages.append("No repository link or file was provided!")
            context = {'messages':messages}
            return render(request, "tool/home.html",context=context)

# @login_required(login_url='login')       
def zip_process(request):
    messages = []
    if request.method == 'POST':
        if request.FILES['zip_file']:
            try:
                # Getting Start time
                start_time = datetime.now()


                if not request.FILES['zip_file'].name.endswith(".zip"):
                    messages.append(f'This is not a ZIP file.')
                    print("This is not a ZIP file.")
                    context = {'messages':messages}
                    return render(request, "tool/home.html",context=context)
                
                output = ''
                zip_file = request.FILES['zip_file']
                
                file_name = zip_file.name.replace(" ", "-")
                BASE_DIR = Path(__file__).resolve().parent
                WORKING_DIR = os.path.join(BASE_DIR, "SensitivityTool", 'projects')
                project_ID = file_name[:-4] + "-" + str(int(time.time() * 1000))
                print("Here-1", project_ID)
                file_path = os.path.join(WORKING_DIR, project_ID)
                print("Here-2",file_path)
                with ZipFile(zip_file) as zObject:
                    zObject.extractall(path=f"{file_path}")
                

                os.chdir(os.path.join(BASE_DIR, "SensitivityTool"))

                output = analyzer(file_path,project_ID)
                print('After OUTPUT')
                print(output)
                files_to_zip = []
                for root, dirs, files in os.walk(output):
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        relative_path = os.path.relpath(file_path, output)
                        files_to_zip.append((relative_path, open(file_path, 'rb').read()))

                # Create a temporary zip file
                zip_file_path = f'Output/{project_ID}.zip'  
                print(zip_file_path)
                with zipfile.ZipFile(zip_file_path, 'w') as zip_file:
                    for file_name, file_content in files_to_zip:
                        zip_file.writestr(file_name, file_content)
                
                if request.user.is_authenticated:
                    username = request.user
                else:
                    username = None
                
                obj= Job.objects.create(
                                    user=username, 
                                    name= f'{file_name[:-4]}.zip'
                                )
                with open(zip_file_path,mode="rb") as f:
                    obj.result = File(f, name=f'{project_ID}.zip')
                    obj.save()
                


                # Bar Chart
                df = pd.read_csv(os.path.join(output,"Sorted Normalized Type Statistic.csv"))

                # Find all rows where the "SENSITIVITY LEVEL" column has non-zero values
                non_zero_sensitivity_rows = df[df['SENSITIVITY LEVEL'] != 0].head(30)

                # Extract class names and sensitivity levels
                class_names = non_zero_sensitivity_rows['CLASS NAME'].tolist()
                sensitivity_levels = non_zero_sensitivity_rows['SENSITIVITY LEVEL'].tolist()

                data = {
                    'class_names': class_names,
                    'sensitivity_levels': sensitivity_levels,
                }

                # Getting End time
                end_time = datetime.now()

                # Calculate and print the time difference
                execution_time = time_difference(start_time, end_time)
            except Exception as e:
                print(e)
                messages.append(f"Error: {e}")
                context = {'messages':messages}
                return render(request, "tool/home.html",context=context)
            finally:
                # #Check prject and delete it at the end
                if os.path.exists(file_path):
                    try:
                        shutil.rmtree(file_path)
                    except Exception as e:
                        print(e)
                
                if os.path.exists(output):
                    try:
                        shutil.rmtree(output)
                    except Exception as e:
                        print(e)
        
        # Go to results page
            return render(request, "tool/results.html", context={'data': data, 'zip': obj, 'time': execution_time})
            
    else:
        messages.append("No repository link or file was provided!")
        context = {'messages':messages}
        return render(request, "tool/home.html",context=context)


# @login_required(login_url='login')
def report_view(request):   
    jobs = Job.objects.all().order_by('-created_at')
    return render(request, "tool/reports.html", context={'jobs': jobs})

# def login_view(request):
    
#     if request.method == 'POST':
#         print("Here")
#         return HttpResponseRedirect(reverse('index'))

    
#     return render(request, "tool/login.html")

def login_view(request):
    message = None

    if request.method == 'POST':

        user = authenticate(request, username=request.POST.get('username'), password=request.POST.get('password'))
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse('index'))

        else:
            message = ('invalid credentials!')

    #if GET request
    #if user is logged in already
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('index'))

    return render(request, "tool/login.html", {'message': message})

def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse('index'))



def logging(log):
    #Will update late
    print(log)

def download_zip(request, name):
    # Retrieve the Job instance
    job = Job.objects.filter(result=name)[0]
    BASE_DIR = Path(__file__).resolve().parent
    # os.chdir(os.path.join(BASE_DIR, "SensitivityTool"))
    # Open the zip file associated with the Job instance
    if job:
        print(os.getcwd())
        print(os.path.exists(os.path.join(BASE_DIR, "SensitivityTool",'Output',job.result.name.split("/")[1])))
        print("HELLOOS: ", os.path.join(BASE_DIR, "SensitivityTool",'Output',job.result.name.split("/")[1]))
        with open(os.path.join(BASE_DIR, "SensitivityTool",'Output',job.result.name.split("/")[1]), 'rb') as zip_file:
            # Create a response with the zip file contents
            response = HttpResponse(zip_file.read(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{job.result.name}"'

    return response

def edit_key_view(request):
    file_path = 'tool/SensitivityTool/Config/Keywords Dictionary.csv'
    if request.method == 'POST':
        data = []
        row_count = int(request.POST.get('row_count', 0))
        for i in range(row_count):
            row = []
            col_count = int(request.POST.get(f'col_count_{i}', 0))
            for j in range(col_count):
                cell_name = f'cell_{i}_{j}'
                cell_value = request.POST.get(cell_name, '')
                row.append(cell_value)
            data.append(row)
        
        write_csv(file_path, data)
        return redirect('edit_keywords_dictionary')

    data = read_csv(file_path)
    return render(request, 'tool/KeywordsDict.html', {'data': data})
