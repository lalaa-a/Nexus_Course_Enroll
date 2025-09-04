// Global variables
let currentUser = null;
let authToken = null;

// API Base URLs
const API_URLS = {
    auth: 'http://127.0.0.1:8001',
    student: 'http://127.0.0.1:8002',
    faculty: 'http://127.0.0.1:8003',
    admin: 'http://127.0.0.1:8004',
    notification: 'http://127.0.0.1:8005'
};

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    checkAuthStatus();
});

function setupEventListeners() {
    // Login form
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    
    // Sign-up form
    document.getElementById('signupForm').addEventListener('submit', handleSignup);
    
    // Course creation form
    document.getElementById('createCourseForm').addEventListener('submit', handleCreateCourse);
    
    // User creation form
    document.getElementById('createUserForm').addEventListener('submit', handleCreateUser);
    
    // Navigation buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const section = this.getAttribute('data-section');
            showSection(section);
            
            // Update active nav button
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

// Authentication functions
async function handleLogin(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();
    
    try {
        const response = await fetch(`${API_URLS.auth}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password })
        });
        
        if (response.ok) {
            const data = await response.json();
            currentUser = data.user;
            authToken = data.access_token;
            
            showDashboard(currentUser.role);
            showAlert('Login successful!', 'success');
        } else {
            const error = await response.json();
            console.log(error);
            showAlert(error.detail || 'Login failed', 'error');
        }
    } catch (error) {
        showAlert('Connection error. Please check if services are running.', 'error');
    }
}

function logout() {
    currentUser = null;
    authToken = null;
    
    // Hide all dashboards
    document.querySelectorAll('.dashboard').forEach(d => d.style.display = 'none');
    document.getElementById('loginContainer').style.display = 'block';
    
    // Clear forms
    document.getElementById('loginForm').reset();
}

function checkAuthStatus() {
    // For demo purposes, start with login screen
    document.getElementById('loginContainer').style.display = 'block';
}

function showDashboard(role) {
    document.getElementById('loginContainer').style.display = 'none';
    
    // Hide all dashboards first
    document.querySelectorAll('.dashboard').forEach(d => d.style.display = 'none');
    
    // Show appropriate dashboard
    switch(role) {
        case 'student':
            document.getElementById('studentDashboard').style.display = 'block';
            loadStudentData();
            break;
        case 'faculty':
            document.getElementById('facultyDashboard').style.display = 'block';
            loadFacultyData();
            break;
        case 'admin':
            document.getElementById('adminDashboard').style.display = 'block';
            loadAdminData();
            break;
    }
}

function showSection(sectionId) {
    // Hide all sections
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    
    // Show selected section
    document.getElementById(sectionId).classList.add('active');
    
    // Load section-specific data
    loadSectionData(sectionId);
}

function loadSectionData(sectionId) {
    switch(sectionId) {
        case 'course-browse':
            searchCourses();
            break;
        case 'my-schedule':
            loadStudentSchedule();
            break;
        case 'my-grades':
            loadStudentGrades();
            break;
        case 'notifications':
            loadNotifications();
            break;
        case 'my-courses':
            loadFacultyCourses();
            break;
        case 'grade-submission':
            loadGradeSubmissionForm();
            break;
        case 'course-management':
            loadCourseManagement();
            break;
        case 'course-admin':
            loadAdminCourses();
            break;
        case 'user-admin':
            loadAdminUsers();
            break;
        case 'reports':
            // Reports are loaded on demand via buttons
            break;
    }
}

// Student Functions
async function loadStudentData() {
    searchCourses();
}

async function searchCourses() {
    const keyword = document.getElementById('courseSearch')?.value || '';
    const department = document.getElementById('departmentFilter')?.value || '';
    const instructor = document.getElementById('instructorFilter')?.value || '';
    
    try {
        let url = `${API_URLS.student}/courses?`;
        if (keyword) url += `keyword=${encodeURIComponent(keyword)}&`;
        if (department) url += `department=${encodeURIComponent(department)}&`;
        if (instructor) url += `instructor=${encodeURIComponent(instructor)}&`;
        
        const response = await fetch(url);
        const courses = await response.json();
        
        displayCourses(courses);
    } catch (error) {
        showAlert('Error loading courses', 'error');
    }
}

function displayCourses(courses) {
    const courseList = document.getElementById('courseList');
    
    if (courses.length === 0) {
        courseList.innerHTML = '<p>No courses found matching your criteria.</p>';
        return;
    }
    
    courseList.innerHTML = courses.map(course => `
        <div class="course-card">
            <div class="course-header">
                <div class="course-info">
                    <h4>${course.name}</h4>
                    <div class="course-code">${course.course_code}</div>
                </div>
                <div class="course-status">
                    <div class="capacity-info">${course.enrolled_count}/${course.capacity} enrolled</div>
                    <div class="capacity-bar">
                        <div class="capacity-fill" style="width: ${(course.enrolled_count/course.capacity)*100}%"></div>
                    </div>
                </div>
            </div>
            <div class="course-details">
                <p><strong>Description:</strong> ${course.description}</p>
                <p><strong>Instructor:</strong> ${course.instructor_name}</p>
                <p><strong>Schedule:</strong> ${course.schedule}</p>
                <p><strong>Location:</strong> ${course.location}</p>
                <p><strong>Credits:</strong> ${course.credits}</p>
                ${course.prerequisites.length > 0 ? `<p><strong>Prerequisites:</strong> ${course.prerequisites.join(', ')}</p>` : ''}
            </div>
            <div class="course-actions">
                <button class="btn btn-success" onclick="enrollInCourse('${course.id}')">
                    ${course.enrolled_count >= course.capacity ? 'Join Waitlist' : 'Enroll'}
                </button>
                <button class="btn btn-secondary" onclick="viewCourseDetails('${course.id}')">View Details</button>
            </div>
        </div>
    `).join('');
}

async function enrollInCourse(courseId) {
    if (!currentUser) return;
    
    try {
        const response = await fetch(`${API_URLS.student}/enroll`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                student_id: currentUser.id,
                course_id: courseId,
                semester: 'Fall 2024'
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            showAlert(result.message, 'success');
            searchCourses(); // Refresh course list
        } else {
            const error = await response.json();
            showAlert(error.detail, 'error');
        }
    } catch (error) {
        showAlert('Error enrolling in course', 'error');
    }
}

async function loadStudentSchedule() {
    if (!currentUser) return;
    
    const semester = document.getElementById('semesterSelect').value;
    
    try {
        const response = await fetch(`${API_URLS.student}/students/${currentUser.id}/schedule?semester=${semester}`);
        const schedule = await response.json();
        
        displaySchedule(schedule.courses);
    } catch (error) {
        showAlert('Error loading schedule', 'error');
    }
}

function displaySchedule(courses) {
    const scheduleView = document.getElementById('scheduleView');
    
    if (courses.length === 0) {
        scheduleView.innerHTML = '<p>No courses enrolled for this semester.</p>';
        return;
    }
    
    scheduleView.innerHTML = courses.map(course => `
        <div class="schedule-item">
            <h4>${course.name} (${course.course_code})</h4>
            <div class="schedule-details">
                <div><strong>Instructor:</strong> ${course.instructor_name}</div>
                <div><strong>Schedule:</strong> ${course.schedule}</div>
                <div><strong>Location:</strong> ${course.location}</div>
                <div><strong>Credits:</strong> ${course.credits}</div>
            </div>
        </div>
    `).join('');
}

async function loadStudentGrades() {
    if (!currentUser) return;
    
    try {
        const response = await fetch(`${API_URLS.student}/students/${currentUser.id}/grades`);
        const grades = await response.json();
        
        displayGrades(grades);
    } catch (error) {
        showAlert('Error loading grades', 'error');
    }
}

function displayGrades(grades) {
    const gradesView = document.getElementById('gradesView');
    
    if (grades.length === 0) {
        gradesView.innerHTML = '<p>No grades available yet.</p>';
        return;
    }
    
    gradesView.innerHTML = grades.map(grade => `
        <div class="grade-item">
            <div class="grade-info">
                <h4>${grade.course_id}</h4>
                <div class="grade-details">
                    <div>Semester: ${grade.semester}</div>
                    <div>Status: ${grade.status}</div>
                </div>
            </div>
            <div class="grade-value">${grade.grade}</div>
        </div>
    `).join('');
}

// Faculty Functions
async function loadFacultyData() {
    loadFacultyCourses();
}

async function loadFacultyCourses() {
    if (!currentUser) return;
    
    try {
        const response = await fetch(`${API_URLS.faculty}/faculty/${currentUser.id}/courses`);
        const courses = await response.json();
        
        displayFacultyCourses(courses);
        populateGradesCourseSelect(courses);
    } catch (error) {
        showAlert('Error loading courses', 'error');
    }
}

function displayFacultyCourses(courses) {
    const coursesList = document.getElementById('facultyCoursesList');
    
    coursesList.innerHTML = courses.map(course => `
        <div class="course-card">
            <div class="course-header">
                <div class="course-info">
                    <h4>${course.name} (${course.course_code})</h4>
                </div>
                <div class="course-status">
                    <div class="capacity-info">${course.enrolled_count}/${course.capacity} enrolled</div>
                </div>
            </div>
            <div class="course-details">
                <p><strong>Schedule:</strong> ${course.schedule}</p>
                <p><strong>Location:</strong> ${course.location}</p>
            </div>
            <div class="course-actions">
                <button class="btn btn-primary" onclick="viewCourseRoster('${course.id}')">View Roster</button>
                <button class="btn btn-secondary" onclick="viewCourseGrades('${course.id}')">View Grades</button>
            </div>
        </div>
    `).join('');
}

async function viewCourseRoster(courseId) {
    try {
        const response = await fetch(`${API_URLS.faculty}/courses/${courseId}/roster`);
        const rosterData = await response.json();
        
        showRosterModal(rosterData);
    } catch (error) {
        showAlert('Error loading roster', 'error');
    }
}

function showRosterModal(rosterData) {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.display = 'block';
    
    modal.innerHTML = `
        <div class="modal-content">
            <span class="close" onclick="this.parentElement.parentElement.remove()">&times;</span>
            <h4>Course Roster - ${rosterData.course.name}</h4>
            <p>Total Enrolled: ${rosterData.enrollment_count}</p>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Student Name</th>
                        <th>Email</th>
                        <th>Enrollment Date</th>
                    </tr>
                </thead>
                <tbody>
                    ${rosterData.enrolled_students.map(student => `
                        <tr>
                            <td>${student.name}</td>
                            <td>${student.email}</td>
                            <td>${new Date(student.enrollment_date).toLocaleDateString()}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
    
    document.body.appendChild(modal);
}

function populateGradesCourseSelect(courses) {
    const select = document.getElementById('gradesCourseSelect');
    select.innerHTML = '<option value="">Select a course...</option>' +
        courses.map(course => `<option value="${course.id}">${course.name} (${course.course_code})</option>`).join('');
    
    select.addEventListener('change', function() {
        if (this.value) {
            loadGradeSubmissionForm(this.value);
        }
    });
}

async function loadGradeSubmissionForm(courseId) {
    if (!courseId) {
        document.getElementById('gradesSubmissionForm').innerHTML = '';
        return;
    }
    
    try {
        const response = await fetch(`${API_URLS.faculty}/courses/${courseId}/roster`);
        const rosterData = await response.json();
        
        displayGradeSubmissionForm(courseId, rosterData.enrolled_students);
    } catch (error) {
        showAlert('Error loading students for grade submission', 'error');
    }
}

function displayGradeSubmissionForm(courseId, students) {
    const form = document.getElementById('gradesSubmissionForm');
    
    form.innerHTML = `
        <form id="submitGradesForm">
            <h4>Submit Grades</h4>
            <div class="grades-list">
                ${students.map(student => `
                    <div class="grade-entry">
                        <label>${student.name}</label>
                        <select name="grade_${student.student_id}" required>
                            <option value="">Select Grade</option>
                            <option value="A">A</option>
                            <option value="B">B</option>
                            <option value="C">C</option>
                            <option value="D">D</option>
                            <option value="F">F</option>
                            <option value="I">I (Incomplete)</option>
                            <option value="W">W (Withdraw)</option>
                        </select>
                    </div>
                `).join('')}
            </div>
            <button type="submit" class="btn btn-primary">Submit Grades</button>
        </form>
    `;
    
    document.getElementById('submitGradesForm').addEventListener('submit', function(e) {
        e.preventDefault();
        submitGrades(courseId, students);
    });
}

async function submitGrades(courseId, students) {
    const formData = new FormData(document.getElementById('submitGradesForm'));
    const grades = [];
    
    students.forEach(student => {
        const grade = formData.get(`grade_${student.student_id}`);
        if (grade) {
            grades.push({
                student_id: student.student_id,
                grade: grade
            });
        }
    });
    
    try {
        const response = await fetch(`${API_URLS.faculty}/courses/${courseId}/grades`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ grades: grades })
        });
        
        if (response.ok) {
            const result = await response.json();
            showAlert(`Submitted ${result.submitted_grades} grades successfully`, 'success');
            if (result.errors.length > 0) {
                showAlert(`Errors: ${result.errors.join(', ')}`, 'warning');
            }
        } else {
            showAlert('Error submitting grades', 'error');
        }
    } catch (error) {
        showAlert('Error submitting grades', 'error');
    }
}

// Admin Functions
async function loadAdminData() {
    loadAdminCourses();
}

async function loadAdminCourses() {
    try {
        const response = await fetch(`${API_URLS.admin}/courses`);
        const courses = await response.json();
        
        displayAdminCourses(courses);
    } catch (error) {
        showAlert('Error loading courses', 'error');
    }
}

function displayAdminCourses(courses) {
    const coursesList = document.getElementById('adminCoursesList');
    
    coursesList.innerHTML = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Course Code</th>
                    <th>Name</th>
                    <th>Instructor</th>
                    <th>Enrollment</th>
                    <th>Department</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${courses.map(course => `
                    <tr>
                        <td>${course.course_code}</td>
                        <td>${course.name}</td>
                        <td>${course.instructor_name}</td>
                        <td>${course.enrolled_count}/${course.capacity}</td>
                        <td>${course.department}</td>
                        <td>
                            <button class="btn btn-secondary" onclick="editCourse('${course.id}')">Edit</button>
                            <button class="btn btn-danger" onclick="deleteCourse('${course.id}')">Delete</button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

function showCreateCourseForm() {
    document.getElementById('createCourseModal').style.display = 'block';
    populateInstructorSelect();
}

function hideCreateCourseForm() {
    document.getElementById('createCourseModal').style.display = 'none';
}

async function populateInstructorSelect() {
    try {
        const response = await fetch(`${API_URLS.admin}/users?role=faculty`);
        const faculty = await response.json();
        
        const select = document.querySelector('#createCourseForm select[name="instructor_id"]');
        select.innerHTML = '<option value="">Select Instructor</option>' +
            faculty.map(f => `<option value="${f.id}">${f.full_name}</option>`).join('');
    } catch (error) {
        console.error('Error loading faculty:', error);
    }
}

async function handleCreateCourse(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const courseData = {};
    
    // Extract form data
    for (let [key, value] of formData.entries()) {
        if (key === 'capacity' || key === 'credits') {
            courseData[key] = parseInt(value);
        } else {
            courseData[key] = value;
        }
    }
    
    // Get instructor name for the selected instructor
    const instructorSelect = document.querySelector('#createCourseForm select[name="instructor_id"]');
    const selectedOption = instructorSelect.options[instructorSelect.selectedIndex];
    courseData.instructor_name = selectedOption.text;
    
    try {
        const response = await fetch(`${API_URLS.admin}/courses`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(courseData)
        });
        
        if (response.ok) {
            const result = await response.json();
            showAlert('Course created successfully!', 'success');
            
            // Clear the form and close modal
            document.getElementById('createCourseForm').reset();
            hideCreateCourseForm();
            
            // Refresh the courses list
            loadAdminCourses();
        } else {
            const error = await response.json();
            showAlert(error.detail || 'Error creating course', 'error');
        }
    } catch (error) {
        showAlert('Connection error. Please check if services are running.', 'error');
    }
}

function showCreateUserForm() {
    document.getElementById('createUserModal').style.display = 'block';
}

function hideCreateUserForm() {
    document.getElementById('createUserModal').style.display = 'none';
}

async function handleCreateUser(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const userData = {};
    
    // Extract form data
    for (let [key, value] of formData.entries()) {
        if (key === 'is_active') {
            userData[key] = true; // checkbox is checked if present
        } else {
            userData[key] = value;
        }
    }
    
    // Set is_active to false if checkbox wasn't checked
    if (!userData.hasOwnProperty('is_active')) {
        userData.is_active = false;
    }
    
    try {
        const response = await fetch(`${API_URLS.admin}/users`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(userData)
        });
        
        if (response.ok) {
            const result = await response.json();
            showAlert('User created successfully!', 'success');
            
            // Clear the form and close modal
            document.getElementById('createUserForm').reset();
            hideCreateUserForm();
            
            // Refresh the users list
            loadAdminUsers();
        } else {
            const error = await response.json();
            showAlert(error.detail || 'Error creating user', 'error');
        }
    } catch (error) {
        showAlert('Connection error. Please check if services are running.', 'error');
    }
}

async function loadAdminUsers() {
    try {
        const response = await fetch(`${API_URLS.admin}/users`);
        const users = await response.json();
        
        displayAdminUsers(users);
    } catch (error) {
        showAlert('Error loading users', 'error');
    }
}

function displayAdminUsers(users) {
    const usersList = document.getElementById('adminUsersList');
    
    usersList.innerHTML = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Username</th>
                    <th>Full Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${users.map(user => `
                    <tr>
                        <td>${user.username}</td>
                        <td>${user.full_name}</td>
                        <td>${user.email}</td>
                        <td>${user.role}</td>
                        <td>${user.is_active ? 'Active' : 'Inactive'}</td>
                        <td>
                            <button class="btn btn-secondary" onclick="editUser('${user.id}')">Edit</button>
                            <button class="btn btn-${user.is_active ? 'warning' : 'success'}" onclick="toggleUserStatus('${user.id}')">
                                ${user.is_active ? 'Deactivate' : 'Activate'}
                            </button>
                            <button class="btn btn-danger" onclick="deleteUser('${user.id}')">Delete</button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

async function toggleUserStatus(userId) {
    try {
        const response = await fetch(`${API_URLS.admin}/users/${userId}/deactivate`, {
            method: 'PUT'
        });
        
        if (response.ok) {
            showAlert('User status updated successfully!', 'success');
            loadAdminUsers(); // Refresh the list
        } else {
            showAlert('Error updating user status', 'error');
        }
    } catch (error) {
        showAlert('Connection error. Please check if services are running.', 'error');
    }
}

function editUser(userId) {
    // Placeholder for edit functionality
    showAlert('Edit functionality not implemented yet', 'warning');
}

// Course Management Functions
function editCourse(courseId) {
    showAlert('Edit functionality not implemented yet', 'warning');
}

async function deleteCourse(courseId) {
    if (!confirm('Are you sure you want to delete this course? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URLS.admin}/courses/${courseId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showAlert('Course deleted successfully!', 'success');
            loadAdminCourses(); // Refresh the list
        } else {
            const error = await response.json();
            showAlert(error.detail || 'Error deleting course', 'error');
        }
    } catch (error) {
        showAlert('Connection error. Please check if services are running.', 'error');
    }
}

async function deleteUser(userId) {
    if (!confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URLS.admin}/users/${userId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showAlert('User deleted successfully!', 'success');
            loadAdminUsers(); // Refresh the list
        } else {
            const error = await response.json();
            showAlert(error.detail || 'Error deleting user', 'error');
        }
    } catch (error) {
        showAlert('Connection error. Please check if services are running.', 'error');
    }
}

// Utility Functions
async function loadNotifications() {
    if (!currentUser) return;
    
    try {
        const response = await fetch(`${API_URLS.notification}/users/${currentUser.id}/notifications`);
        const notifications = await response.json();
        
        displayNotifications(notifications);
    } catch (error) {
        showAlert('Error loading notifications', 'error');
    }
}

function displayNotifications(notifications) {
    const notificationsList = document.getElementById('notificationsList');
    
    if (notifications.length === 0) {
        notificationsList.innerHTML = '<p>No notifications.</p>';
        return;
    }
    
    notificationsList.innerHTML = notifications.map(notification => `
        <div class="notification-item ${notification.is_read ? '' : 'unread'}">
            <div class="notification-header">
                <span class="notification-type">${notification.type}</span>
                <span class="notification-date">${new Date(notification.created_at).toLocaleDateString()}</span>
            </div>
            <p>${notification.message}</p>
            ${!notification.is_read ? `<button class="btn btn-secondary" onclick="markNotificationRead('${notification.id}')">Mark as Read</button>` : ''}
        </div>
    `).join('');
}

async function markNotificationRead(notificationId) {
    try {
        await fetch(`${API_URLS.notification}/notifications/${notificationId}/read`, {
            method: 'PUT'
        });
        loadNotifications(); // Refresh
    } catch (error) {
        showAlert('Error marking notification as read', 'error');
    }
}


/*
function showAlert(message, type) {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    
    // Insert at the top of the current content area
    const content = document.querySelector('.section.active') || document.querySelector('.content');
    if (content) {
        content.insertBefore(alert, content.firstChild);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.parentNode.removeChild(alert);
            }
        }, 5000);
    }
}
*/


function showAlert(message, type) {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;

    const container = document.getElementById('alert-container');
    container.insertBefore(alert, container.firstChild);

    setTimeout(() => {
        if (alert.parentNode) {
            alert.parentNode.removeChild(alert);
        }
    }, 5000);
}
  




// Report Functions
async function loadEnrollmentStats() {
    try {
        const response = await fetch(`${API_URLS.admin}/reports/enrollment-stats`);
        const stats = await response.json();
        
        displayReport('Enrollment Statistics', stats);
    } catch (error) {
        showAlert('Error loading enrollment statistics', 'error');
    }
}

async function loadFacultyWorkload() {
    try {
        const response = await fetch(`${API_URLS.admin}/reports/faculty-workload`);
        const workload = await response.json();
        
        displayReport('Faculty Workload Report', workload);
    } catch (error) {
        showAlert('Error loading faculty workload', 'error');
    }
}

async function loadCoursePopularity() {
    try {
        const response = await fetch(`${API_URLS.admin}/reports/course-popularity`);
        const popularity = await response.json();
        
        displayReport('Course Popularity Trends', popularity);
    } catch (error) {
        showAlert('Error loading course popularity', 'error');
    }
}

async function loadHighCapacityCourses() {
    try {
        const response = await fetch(`${API_URLS.admin}/reports/high-capacity-courses?threshold=90`);
        const highCapacity = await response.json();
        
        displayReport('High Capacity Courses (>90%)', highCapacity);
    } catch (error) {
        showAlert('Error loading high capacity courses', 'error');
    }
}

function displayReport(title, data) {
    const reportsView = document.getElementById('reportsView');
    reportsView.innerHTML = `
        <h4>${title}</h4>
        <pre>${JSON.stringify(data, null, 2)}</pre>
    `;
}

// Tab switching functions
function showLoginForm() {
    document.getElementById('loginFormContainer').style.display = 'block';
    document.getElementById('signupFormContainer').style.display = 'none';
    
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    
    // Clear forms
    document.getElementById('signupForm').reset();
}

function showSignupForm() {
    document.getElementById('loginFormContainer').style.display = 'none';
    document.getElementById('signupFormContainer').style.display = 'block';
    
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    
    // Clear forms
    document.getElementById('loginForm').reset();
}

// Sign-up form handler
async function handleSignup(e) {
    e.preventDefault();
    
    const fullName = document.getElementById('signupFullName').value.trim();
    const username = document.getElementById('signupUsername').value.trim();
    const email = document.getElementById('signupEmail').value.trim();
    const password = document.getElementById('signupPassword').value.trim();
    const confirmPassword = document.getElementById('signupConfirmPassword').value.trim();
    
    // Client-side validation
    if (password !== confirmPassword) {
        showAlert('Passwords do not match!', 'error');
        return;
    }
    
    if (password.length < 6) {
        showAlert('Password must be at least 6 characters long!', 'error');
        return;
    }
    
    if (username.length < 3) {
        showAlert('Username must be at least 3 characters long!', 'error');
        return;
    }
    
    if (fullName.length < 2) {
        showAlert('Please enter your full name!', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_URLS.auth}/signup`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                password: password,
                email: email,
                full_name: fullName
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            showAlert(data.message, 'success');
            
            // Clear the form
            document.getElementById('signupForm').reset();
            
            // Switch to login form after successful signup
            setTimeout(() => {
                showLoginForm();
                // Pre-fill username in login form
                document.getElementById('username').value = username;
            }, 2000);
            
        } else {
            const error = await response.json();
            showAlert(error.detail || 'Sign-up failed', 'error');
        }
    } catch (error) {
        showAlert('Connection error. Please check if services are running.', 'error');
    }
}
