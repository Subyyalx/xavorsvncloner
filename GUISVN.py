import os
import requests
from bs4 import BeautifulSoup
import subprocess
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import threading

# SVN credentials
username = ''
password = ''

# SVN URL
svn_url = 'http://SVN-Server/svn/'

# Function to scrape repositories
def get_repositories(url):
    response = requests.get(url, auth=(username, password))

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'xml')
        repos = []

        for dir_tag in soup.find_all('dir'):
            repo_name = dir_tag.get('name')
            href = dir_tag.get('href')
            if repo_name and href:
                repos.append(href)

        return repos
    else:
        messagebox.showerror("Error", f"Failed to access SVN URL: {response.status_code}")
        return []

# Function to calculate size of a directory in MB
def get_directory_size(directory):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size / (1024 * 1024)  # Convert bytes to MB

# Function to clone selected repositories
def clone_repos(repos, base_url, target_dir):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    total_repos = len(repos)
    cloned_count = 0

    #log_output("Total Repositories Found: {}".format(total_repos))
    log_output("Selected Repositories: {}".format(len(repos)))

    for index, repo in enumerate(repos, start=1):
        repo_url = base_url + repo
        local_path = os.path.join(target_dir, repo.strip('/'))

        # Create a label for each repository
        repo_status_label = tk.Label(scrollable_frame, bg="#e0e0e0", font=('Arial', 10))
        repo_status_label.pack(anchor="w", padx=10)

        try:
            # Clone the repository
            subprocess.run([
                'svn', 'checkout', repo_url, local_path, '--username', username, '--password', password, '--no-auth-cache'
            ], check=True)

            # Calculate the size of the newly cloned repository
            repo_size = get_directory_size(local_path)

            # Update the status label to green for success
            repo_status_label.config(text=f"Cloned {repo} into {local_path}. Size: {repo_size:.2f} MB", fg="green")
            cloned_count += 1

            # Log success
            log_output(f"Successfully cloned: {repo} (Size: {repo_size:.2f} MB)")

            # Update progress bar and label
            progress_bar['value'] = (index / total_repos) * 100
            progress_label.config(text=f"Cloned {index}/{total_repos} repositories")
            root.update_idletasks()  # Update the GUI

        except subprocess.CalledProcessError as e:
            # Update the status label to red for error
            repo_status_label.config(text=f"Error cloning {repo}: {e}", fg="red")

            # Log error
            log_output(f"Error cloning {repo}: {e}")

    log_output(f"\nTotal Cloned: {cloned_count}/{total_repos}")

# Function to log output to GUI
def log_output(message):
    log_text.config(state=tk.NORMAL)  # Enable editing
    log_text.insert(tk.END, message + "\n")  # Add message to log
    log_text.config(state=tk.DISABLED)  # Disable editing
    log_text.see(tk.END)  # Scroll to the end

# Function to fetch and display repositories in the GUI
def fetch_repositories():
    repositories = get_repositories(svn_url)

    if repositories:
        for widget in scrollable_frame.winfo_children():
            widget.destroy()  # Clear previous repo list if any

        for repo in repositories:
            var = tk.BooleanVar()
            checkbox = tk.Checkbutton(scrollable_frame, text=repo, variable=var, bg="#f0f0f0", font=('Arial', 10))
            checkbox.var = var
            checkbox.repo_name = repo
            checkbox.pack(anchor="w", padx=10, pady=2)
            checkboxes.append(checkbox)

        log_output(f"Fetched {len(repositories)} repositories.")  # Log the number of fetched repositories
        clone_button.config(state=tk.NORMAL)  # Enable clone button after fetching repos
    else:
        messagebox.showwarning("No Repositories", "No repositories found or unable to list repositories.")

# Function to get selected repositories
def get_selected_repositories():
    selected_repos = [cb.repo_name for cb in checkboxes if cb.var.get()]
    if not selected_repos:
        messagebox.showwarning("No Selection", "Please select at least one repository.")
        return []

    return selected_repos

# Function to browse and select a folder
def browse_folder():
    folder = filedialog.askdirectory()
    if folder:
        folder_entry.delete(0, tk.END)
        folder_entry.insert(0, folder)

# Function to handle clone operation in a separate thread
def clone_selected_repos():
    selected_repos = get_selected_repositories()
    target_dir = folder_entry.get()

    if selected_repos and target_dir:
        # Disable all checkboxes
        for checkbox in checkboxes:
            checkbox.config(state=tk.DISABLED)

        progress_bar['value'] = 0  # Reset progress bar
        progress_label.config(text="Starting clone...")
        log_output("Cloning started...")

        # Run cloning in a separate thread
        cloning_thread = threading.Thread(target=clone_repos, args=(selected_repos, svn_url, target_dir))
        cloning_thread.start()

        # Check if cloning thread is still alive and enable checkboxes when done
        def check_thread():
            if cloning_thread.is_alive():
                root.after(100, check_thread)  # Check again after 100 ms
            else:
                # Re-enable all checkboxes
                for checkbox in checkboxes:
                    checkbox.config(state=tk.NORMAL)
                progress_label.config(text="Clone completed.")
                log_output("Cloning completed.")

        check_thread()

# GUI setup
root = tk.Tk()
root.title("XavorSVNCloner")
root.geometry("600x600")
root.configure(bg="#e0e0e0")

# Create a frame for the scrollbar and canvas
canvas = tk.Canvas(root, bg="#e0e0e0")
scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
scrollable_frame = tk.Frame(canvas, bg="#e0e0e0")

# Configure the canvas
scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

# Add the scrollbar to the canvas
canvas.configure(yscrollcommand=scrollbar.set)

# Pack the canvas and scrollbar
canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# Button to fetch repositories
fetch_button = tk.Button(root, text="Fetch Repositories", command=fetch_repositories, bg="#4CAF50", fg="white", font=('Arial', 12, 'bold'), relief=tk.FLAT)
fetch_button.pack(pady=10)

# Entry for target folder
folder_label = tk.Label(root, text="Select Folder:", bg="#e0e0e0", font=('Arial', 10))
folder_label.pack(anchor="w", padx=10)

folder_entry = tk.Entry(root, width=50)
folder_entry.pack(padx=10)

browse_button = tk.Button(root, text="Browse", command=browse_folder, bg="#2196F3", fg="white", font=('Arial', 10), relief=tk.FLAT)
browse_button.pack(pady=5)

# Clone button
clone_button = tk.Button(root, text="Clone Selected Repositories", command=clone_selected_repos, state=tk.DISABLED, bg="#FF5722", fg="white", font=('Arial', 12, 'bold'), relief=tk.FLAT)
clone_button.pack(pady=10)

# Progress label
progress_label = tk.Label(root, text="", bg="#e0e0e0", font=('Arial', 10))
progress_label.pack(pady=5)

# Progress bar
progress_bar = ttk.Progressbar(root, length=400, mode='determinate')
progress_bar.pack(pady=5)

# Log output area
log_label = tk.Label(root, text="Log Output:", bg="#e0e0e0", font=('Arial', 10))
log_label.pack(anchor="w", padx=10)

log_text = tk.Text(root, height=10, width=60, bg="#f0f0f0", font=('Arial', 10), state=tk.DISABLED)
log_text.pack(padx=10, pady=5)

# Store references to checkboxes
checkboxes = []

root.mainloop()
