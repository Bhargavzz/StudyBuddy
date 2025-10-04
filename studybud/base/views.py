from django.shortcuts import render,redirect
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Room,Topic,Message,User
from django.conf import settings
from django.contrib.auth import authenticate,login,logout
from.forms import RoomForm,UserForm,MyUserCreationForm
from supabase import create_client
import os
# Create your views here.

# rooms = [
#     {'id': 1, 'name':'Lets learn python!'},
#     {'id': 2, 'name':'Design with me'},
#     {'id': 3, 'name':'GoLang Developers'},
# ]
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def upload_to_supabase(file_obj, file_name):
    bucket = "avatars"
    # Try to delete the file first (ignore error if it doesn't exist)
    supabase.storage.from_(bucket).remove([file_name])
    file_bytes = file_obj.read()
    res = supabase.storage.from_(bucket).upload(file_name, file_bytes)
    # Check for status_code or raise_for_status
    if hasattr(res, "status_code") and not (200 <= res.status_code < 300):
        raise Exception(f"Upload failed: {getattr(res, 'data', res)}")
    url = supabase.storage.from_(bucket).get_public_url(file_name)
    return url

def loginPage(request):
    page = 'login'
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        email = request.POST.get('email').lower()
        password = request.POST.get('password')
        
        try:
            user=User.objects.get(email=email)
        
        except:   
            messages.error(request,'User does not exist') 
            
        user = authenticate(request,email=email,password=password)
        
        if user is not None:
            login(request,user)
            return redirect('home')
        
        else:
            messages.error(request, 'Username or Password is incorrect')
            
        
    context = {'page':page}
    return render(request, 'base/login_register.html',context)


def logoutUser(request):
    logout(request)
    return redirect('home')

def registerPage(request):
    page = 'register'
    form=MyUserCreationForm()
    
    if request.method =='POST':
        form=MyUserCreationForm(request.POST)
        if form.is_valid():
            user=form.save(commit=False)
            user.username = user.username.lower()
            user.save()
            login(request,user)
            return redirect('home')
        else:
            messages.error(request,'An error occured during registration')
    return render(request, 'base/login_register.html',{'form':form})

def home(request):
    q = request.GET.get('q') if request.GET.get('q') !=None else ' '
    rooms = Room.objects.filter(
          Q(topic__name__icontains=q) |
          Q(name__icontains=q) |
          Q(description__icontains=q)         
                                
         ) 
    
    topics = Topic.objects.all()[0:5]
    room_count  = rooms.count()
    room_messages = Message.objects.all().order_by('-created')[:5]  # Get all messages, latest first

    
    context = {'rooms': rooms,'topics':topics,
               'room_count':room_count,'room_messages':room_messages}
    return render(request, 'base/home.html',context)


def room(request,pk):
    # room = None
    # for i in rooms:
    #     if i['id'] == int(pk):
    #         room = i
    room = Room.objects.get(id=pk)
    room_messages=room.message_set.all().order_by('created')  # Changed to ascending order (oldest first)
    participants = room.participants.all()
    if request.method=='POST':
        body = request.POST.get('body')
        if body:  # Ensure body is not empty
            Message.objects.create(
                user=request.user,
                room=room,
                body=body,
                username=request.user.username,
                avatar_url=request.user.avatar if request.user.avatar else 'https://avatar.iran.liara.run/public/17'
            )
        room.participants.add(request.user)
        
        # If it's an AJAX request (from our JavaScript), return JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.http import JsonResponse
            return JsonResponse({'status': 'success'})
        
        # Otherwise, redirect (for users without JavaScript)
        return redirect('room',pk=room.id)
    
    
    context ={'room': room,
              'room_messages':room_messages,
              'participants':participants,
              'SUPABASE_URL': settings.SUPABASE_URL,
              'SUPABASE_ANON_KEY': settings.SUPABASE_ANON_KEY
        }
    return render(request,'base/room.html',context)



def userProfile(request,pk):
    user=User.objects.get(id=pk)
    rooms=user.room_set.all()
    room_messages=user.message_set.all()
    topics=Topic.objects.all()
    context = {'user':user,'rooms':rooms,'room_messages':room_messages,'topics':topics}
    return render(request,'base/profile.html',context)


@login_required(login_url='login')

def createRoom(request):
    form = RoomForm()
    topics = Topic.objects.all()
    if request.method == 'POST' :
        topic_name = request.POST.get('topic')
        topic, created = Topic.objects.get_or_create(name=topic_name)
        
        Room.objects.create(
            host=request.user,
            topic=topic,
            name=request.POST.get('name'),
            description=request.POST.get('description')
        )
        return redirect('home')
    context={'form':form, 'topics':topics}
    return render(request,'base/room_form.html',context)

@login_required(login_url='login')
def updateRoom(request, pk):
    room = Room.objects.get(id=pk)
    form = RoomForm(instance=room)
    topics = Topic.objects.all()
    if request.user != room.host:
        return HttpResponse('You are not allowed here!!')
    
    if request.method == 'POST':
        topic_name = request.POST.get('topic')
        topic, created = Topic.objects.get_or_create(name=topic_name)
        room.name = request.POST.get('name')
        room.topic = topic
        room.description = request.POST.get('description')
        room.save()
        return redirect('home')
        
             
    
    context={'form': form, 'topics':topics,'room':room }
    return render(request, 'base/room_form.html',context)





@login_required(login_url='login')
def deleteRoom(request,pk):
    room = Room.objects.get(id=pk)
    
    if request.user != room.host:
        return HttpResponse('You are not allowed here!!')
   
   
    if request.method == 'POST':
        room.delete()
        return redirect('home')
         
    return render(request,'base/delete.html', {'obj':room})



@login_required(login_url='login')
def deleteMessage(request,pk):
    message = Message.objects.get(id=pk)
    
    if request.user != message.user:
        return HttpResponse('You are not allowed here!!')
   
   
    if request.method == 'POST':
        message.delete()
        return redirect('home')
         
    return render(request,'base/delete.html', {'obj':message})



@login_required(login_url='login')
def updateUser(request):
    user = request.user
    form = UserForm(instance=user)
    
    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            avatar_file = request.FILES.get('avatar')
            if avatar_file:
                file_name = f"{user.username}_{avatar_file.name}"
                avatar_url = upload_to_supabase(avatar_file, file_name)
                user.avatar = avatar_url
                user.save()
            else:
                form.save()
            return redirect('user-profile', pk=user.id)
    context = {'form': form}
    return render(request, 'base/update-user.html', context)


def topicsPage(request):
    q = request.GET.get('q', '')  # Default to an empty string if no query
    if q:  # If there's a search term
        topics = Topic.objects.filter(name__icontains=q)
    else:  # Otherwise, fetch all topics
        topics = Topic.objects.all()
    return render(request, 'base/topics.html', {'topics': topics})

def activityPage(request):
    room_messages = Message.objects.all().order_by('-created')[:5] 
    return render(request,'base/activity.html',{'room_messages':room_messages})

def room_participants(request, room_id):
    room = Room.objects.get(id=room_id)
    users = room.participants.all()
    data = [
        {
            "id": user.id,
            "name": user.name,
            "username": user.username,
            "avatar_url": user.avatar if user.avatar else "https://avatar.iran.liara.run/public/17"
        }
        for user in users
    ]
    return JsonResponse(data, safe=False)

@login_required
def sync_offline_messages(request):
    """
    API endpoint to sync offline messages when network returns.
    Expects JSON: {"room_id": 123, "messages": [{"client_id": "uuid", "body": "text", "timestamp": "iso"}]}
    """
    if request.method != 'POST':
        return JsonResponse({"error": "POST only"}, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        room_id = data.get('room_id')
        messages = data.get('messages', [])
        
        if not room_id:
            return JsonResponse({"error": "room_id required"}, status=400)
            
        room = Room.objects.get(id=room_id)
        synced_messages = []
        
        for msg_data in messages:
            client_id = msg_data.get('client_id')
            body = msg_data.get('body', '').strip()
            
            if not body or not client_id:
                continue
                
            # Check if message already exists (deduplication)
            existing = Message.objects.filter(
                user=request.user,
                room=room,
                body=body
            ).first()
            
            if not existing:
                # Save new message
                message = Message.objects.create(
                    user=request.user,
                    room=room,
                    body=body,
                    username=request.user.username,
                    avatar_url=request.user.avatar if request.user.avatar else 'https://avatar.iran.liara.run/public/17'
                )
                room.participants.add(request.user)
                
                synced_messages.append({
                    "client_id": client_id,
                    "server_id": message.id,
                    "synced": True
                })
            else:
                # Already exists, mark as synced
                synced_messages.append({
                    "client_id": client_id,
                    "server_id": existing.id,
                    "synced": True,
                    "duplicate": True
                })
        
        return JsonResponse({
            "success": True,
            "synced_messages": synced_messages
        })
        
    except Room.DoesNotExist:
        return JsonResponse({"error": "Room not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
