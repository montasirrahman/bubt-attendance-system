// Global JavaScript functions for BUBT Attendance System

$(document).ready(function () {
  // Initialize tooltips
  $('[data-bs-toggle="tooltip"]').tooltip();

  // Auto-hide alerts after 5 seconds
  setTimeout(function () {
    $(".alert").alert("close");
  }, 5000);

  // Form validation enhancement
  $("form").on("submit", function (e) {
    const requiredFields = $(this).find("[required]");
    let valid = true;

    requiredFields.each(function () {
      if (!$(this).val().trim()) {
        valid = false;
        $(this).addClass("is-invalid");
      } else {
        $(this).removeClass("is-invalid");
      }
    });

    if (!valid) {
      e.preventDefault();
      showToast("Please fill in all required fields.", "warning");
    }
  });

  // Real-time attendance counter update
  if (typeof updateAttendanceCounter === "undefined") {
    window.updateAttendanceCounter = function () {
      $.get("/get_attendance_stats", function (data) {
        $("#attendanceCounter").text(data.count);
      });
    };
  }

  // Prevent multiple form submissions
  $(document).on("submit", "form", function () {
    const $form = $(this);
    const $submitBtn = $form.find('button[type="submit"]');

    if ($form.data("submitting")) {
      return false;
    }

    $form.data("submitting", true);
    $submitBtn
      .prop("disabled", true)
      .html('<i class="fas fa-spinner fa-spin me-2"></i>Processing...');

    // Re-enable after 3 seconds in case of error
    setTimeout(() => {
      $form.data("submitting", false);
      $submitBtn
        .prop("disabled", false)
        .html($submitBtn.data("original-text") || "Submit");
    }, 3000);
  });

  // Store original button text
  $('button[type="submit"]').each(function () {
    $(this).data("original-text", $(this).html());
  });

  // Add escape key to close toasts
  $(document).on("keydown", function (e) {
    if (e.key === "Escape") {
      $(".toast").toast("hide");
    }
  });
});

// Toast notification function
function showToast(message, type = "info") {
  const toastContainer = $("#toast-container");
  if (toastContainer.length === 0) {
    $("body").append(
      '<div id="toast-container" class="toast-container position-fixed top-0 end-0 p-3"></div>'
    );
  }

  const toastId = "toast-" + Date.now();
  const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-white bg-${type} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;

  $("#toast-container").append(toastHtml);
  const toastElement = new bootstrap.Toast($("#" + toastId));
  toastElement.show();

  // Remove toast from DOM after it's hidden
  $("#" + toastId).on("hidden.bs.toast", function () {
    $(this).remove();
  });
}

// Image preview for file inputs
function previewImage(input, previewId) {
  const preview = document.getElementById(previewId);
  const file = input.files[0];
  const reader = new FileReader();

  reader.onloadend = function () {
    preview.src = reader.result;
    preview.style.display = "block";
  };

  if (file) {
    reader.readAsDataURL(file);
  } else {
    preview.src = "";
    preview.style.display = "none";
  }
}

// Date formatting helper
function formatDate(dateString) {
  const options = {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
  };
  return new Date(dateString).toLocaleDateString("en-US", options);
}

// Time formatting helper
function formatTime(timeString) {
  return new Date("1970-01-01T" + timeString + "Z").toLocaleTimeString(
    "en-US",
    {
      hour12: true,
      hour: "2-digit",
      minute: "2-digit",
    }
  );
}

// AJAX error handler
$(document).ajaxError(function (event, jqxhr, settings, thrownError) {
  console.error("AJAX Error:", thrownError);
  showToast("An error occurred. Please try again.", "danger");
});

// Page loading indicator
$(document).ajaxStart(function () {
  $("#loadingIndicator").show();
});

$(document).ajaxStop(function () {
  $("#loadingIndicator").hide();
});

// Utility function to check if camera is accessible
function checkCameraAccess() {
  return new Promise((resolve, reject) => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      reject(new Error("Camera API not supported"));
      return;
    }

    navigator.mediaDevices
      .getUserMedia({ video: true })
      .then((stream) => {
        stream.getTracks().forEach((track) => track.stop());
        resolve(true);
      })
      .catch((error) => {
        reject(error);
      });
  });
}

// Export functions for global use
window.BUBT = {
  showToast: showToast,
  formatDate: formatDate,
  formatTime: formatTime,
  checkCameraAccess: checkCameraAccess,
};
