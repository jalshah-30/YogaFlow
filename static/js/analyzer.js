
/* =========================================================
   YogaFlow - AI Yoga Analyzer
   File: static/js/analyzer.js

   Backend endpoint: POST /api/analyze
   Expected upload field: image
   ========================================================= */

(() => {
    "use strict";

    const API_ENDPOINT = "/api/analyze";
    const LIVE_INTERVAL = 1200;

    let cameraStream = null;
    let liveAnalysisRunning = false;
    let analysisInProgress = false;
    let liveTimer = null;
    let requestController = null;

    const $ = (id) => document.getElementById(id);

    function setMessage(id, message, isError = false) {
        const element = $(id);
        if (!element) return;

        element.textContent = message;
        element.classList.toggle("error", isError);
    }

    function setCameraButtons(cameraOn) {
        $("startCameraBtn").disabled = cameraOn;
        $("liveAnalysisBtn").disabled = !cameraOn;
        $("captureBtn").disabled = !cameraOn;
        $("stopCameraBtn").disabled = !cameraOn;
    }

    function showCameraPlaceholder(show) {
        const placeholder = $("cameraPlaceholder");
        const preview = document.querySelector(".camera-preview");

        if (placeholder) {
            placeholder.style.display = show ? "flex" : "none";
        }

        if (preview) {
            preview.classList.toggle("camera-active", !show);
        }
    }

    // ---------------------------------------------------------
    // Camera start
    // ---------------------------------------------------------

    async function startCamera() {
        if (cameraStream) return;

        const video = $("camera");

        if (!navigator.mediaDevices?.getUserMedia) {
            setMessage(
                "liveMessage",
                "Camera access is unavailable. Use localhost or HTTPS.",
                true
            );
            return;
        }

        $("startCameraBtn").disabled = true;
        setMessage("liveMessage", "Requesting camera permission...");

        try {
            cameraStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: "user"
                },
                audio: false
            });

            video.srcObject = cameraStream;
            await video.play();

            showCameraPlaceholder(false);
            $("cameraStatus").textContent = "Camera On";

            setCameraButtons(true);
            setMessage(
                "liveMessage",
                "Camera started. Click Start Live Analysis."
            );

        } catch (error) {
            console.error("Camera startup error:", error);

            if (cameraStream) {
                cameraStream.getTracks().forEach(track => track.stop());
            }

            cameraStream = null;
            video.srcObject = null;
            setCameraButtons(false);
            $("cameraStatus").textContent = "Camera Off";

            let message = error.message || "Unknown camera error.";

            if (error.name === "NotAllowedError") {
                message = "Camera permission denied. Allow camera access in your browser settings.";
            } else if (error.name === "NotFoundError") {
                message = "No camera was found on this device.";
            } else if (error.name === "NotReadableError") {
                message = "Camera is busy. Close other applications using it and retry.";
            }

            setMessage("liveMessage", message, true);
        }
    }

    // ---------------------------------------------------------
    // Send one image to Flask
    // ---------------------------------------------------------

    async function analyzeImage(blob, source) {
        const formData = new FormData();
        formData.append("image", blob, "yoga-frame.jpg");

        const response = await fetch(API_ENDPOINT, {
            method: "POST",
            body: formData
        });

        const contentType = response.headers.get("content-type") || "";

        let data;

        if (contentType.includes("application/json")) {
            data = await response.json();
        } else {
            const text = await response.text();
            throw new Error(
                `Server returned an unexpected response (HTTP ${response.status}). ` +
                text.slice(0, 180)
            );
        }

        if (!response.ok) {
            throw new Error(
                data.error || data.message || `Analysis failed (HTTP ${response.status}).`
            );
        }

        displayResults(data, source);
        return data;
    }

    // ---------------------------------------------------------
    // Capture a frame from the camera
    // ---------------------------------------------------------

    async function captureFrameBlob() {
        const video = $("camera");
        const canvas = $("canvas");

        if (
            !cameraStream ||
            !video.videoWidth ||
            !video.videoHeight
        ) {
            throw new Error("Start the camera and wait for the video preview first.");
        }

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        const context = canvas.getContext("2d");

        if (!context) {
            throw new Error("Could not access the canvas.");
        }

        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        return new Promise((resolve, reject) => {
            canvas.toBlob(
                blob => {
                    if (blob) {
                        resolve(blob);
                    } else {
                        reject(new Error("Could not capture the camera frame."));
                    }
                },
                "image/jpeg",
                0.85
            );
        });
    }

    // ---------------------------------------------------------
    // Analyze one live camera frame
    // ---------------------------------------------------------

    async function analyzeLiveFrame() {
        if (!liveAnalysisRunning || analysisInProgress) return;

        if (!cameraStream) {
            stopLiveAnalysis();
            setMessage("liveMessage", "Start the camera first.", true);
            return;
        }

        analysisInProgress = true;

        try {
            const blob = await captureFrameBlob();

            if (!liveAnalysisRunning) return;

            setMessage("liveMessage", "Analyzing current posture...");

            await analyzeImage(blob, "Live camera analysis");

            if (liveAnalysisRunning) {
                setMessage("liveMessage", "Live posture analysis is running.");
            }

        } catch (error) {
            console.error("Live analysis error:", error);

            if (liveAnalysisRunning) {
                setMessage(
                    "liveMessage",
                    `Analysis failed: ${error.message}`,
                    true
                );
            }
        } finally {
            analysisInProgress = false;

            if (liveAnalysisRunning) {
                liveTimer = setTimeout(analyzeLiveFrame, LIVE_INTERVAL);
            }
        }
    }

    function startLiveAnalysis() {
        if (!cameraStream) {
            setMessage("liveMessage", "Start the camera first.", true);
            return;
        }

        if (liveAnalysisRunning) return;

        liveAnalysisRunning = true;
        $("liveAnalysisBtn").textContent = "Stop Live Analysis";

        setMessage("liveMessage", "Starting live posture analysis...");

        analyzeLiveFrame();
    }

    function stopLiveAnalysis() {
        liveAnalysisRunning = false;

        if (liveTimer) {
            clearTimeout(liveTimer);
            liveTimer = null;
        }

        if (requestController) {
            requestController.abort();
            requestController = null;
        }

        $("liveAnalysisBtn").textContent = "Start Live Analysis";

        if (cameraStream) {
            setMessage("liveMessage", "Live analysis stopped. Camera is still on.");
        }
    }

    // ---------------------------------------------------------
    // Capture and analyze one frame
    // ---------------------------------------------------------

    async function captureAndAnalyze() {
        if (!cameraStream) {
            setMessage("liveMessage", "Start the camera first.", true);
            return;
        }

        if (analysisInProgress) {
            setMessage("liveMessage", "Please wait for the current analysis to finish.");
            return;
        }

        analysisInProgress = true;
        $("captureBtn").disabled = true;

        try {
            const blob = await captureFrameBlob();

            setMessage("liveMessage", "Analyzing captured frame...");
            await analyzeImage(blob, "Captured camera frame");

            setMessage("liveMessage", "Frame analysis complete.");

        } catch (error) {
            console.error("Frame analysis error:", error);
            setMessage("liveMessage", `Analysis failed: ${error.message}`, true);
        } finally {
            analysisInProgress = false;
            $("captureBtn").disabled = !cameraStream;
        }
    }

    // ---------------------------------------------------------
    // Stop camera
    // ---------------------------------------------------------

    function stopCamera() {
        stopLiveAnalysis();

        if (cameraStream) {
            cameraStream.getTracks().forEach(track => track.stop());
            cameraStream = null;
        }

        $("camera").srcObject = null;
        $("cameraStatus").textContent = "Camera Off";

        showCameraPlaceholder(true);
        setCameraButtons(false);

        setMessage("liveMessage", "Camera stopped.");
    }

    // ---------------------------------------------------------
    // Photo upload preview
    // ---------------------------------------------------------

    function handleImageSelection(event) {
        const file = event.target.files?.[0];

        $("uploadBtn").disabled = true;

        if (!file) {
            $("uploadPreviewContainer").hidden = true;
            $("uploadPreview").removeAttribute("src");
            setMessage("uploadMessage", "Select a photo to begin.");
            return;
        }

        if (!["image/jpeg", "image/png"].includes(file.type)) {
            event.target.value = "";
            $("uploadPreviewContainer").hidden = true;
            setMessage("uploadMessage", "Please select a JPG or PNG image.", true);
            return;
        }

        const previousURL = $("uploadPreview").dataset.objectUrl;

        if (previousURL) {
            URL.revokeObjectURL(previousURL);
        }

        const objectURL = URL.createObjectURL(file);

        $("uploadPreview").src = objectURL;
        $("uploadPreview").dataset.objectUrl = objectURL;
        $("uploadPreviewContainer").hidden = false;
        $("uploadBtn").disabled = false;

        setMessage("uploadMessage", `Selected: ${file.name}`);
    }

    function removeSelectedImage() {
        const preview = $("uploadPreview");
        const previousURL = preview.dataset.objectUrl;

        if (previousURL) {
            URL.revokeObjectURL(previousURL);
        }

        preview.removeAttribute("src");
        delete preview.dataset.objectUrl;

        $("imageInput").value = "";
        $("uploadPreviewContainer").hidden = true;
        $("uploadBtn").disabled = true;

        setMessage("uploadMessage", "Select a photo to begin.");
    }

    // ---------------------------------------------------------
    // Analyze uploaded photo
    // ---------------------------------------------------------

    async function analyzeUploadedPhoto() {
        const file = $("imageInput").files?.[0];

        if (!file) {
            setMessage("uploadMessage", "Please select an image first.", true);
            return;
        }

        $("uploadBtn").disabled = true;
        setMessage("uploadMessage", "Analyzing your yoga photo...");

        try {
            await analyzeImage(file, "Uploaded photo analysis");
            setMessage("uploadMessage", "Photo analysis complete.");

        } catch (error) {
            console.error("Photo analysis error:", error);

            setMessage(
                "uploadMessage",
                `Analysis failed: ${error.message}`,
                true
            );
        } finally {
            $("uploadBtn").disabled = false;
        }
    }

    // ---------------------------------------------------------
    // Display backend results
    // ---------------------------------------------------------

    function displayResults(data, source) {
        $("resultSection").hidden = false;
        $("resultSource").textContent = source;

        const pose =
            data.pose ??
            data.predicted_pose ??
            data.prediction ??
            data.predicted_class ??
            data.class_name ??
            "-";

        const confidence =
            data.confidence ??
            data.confidence_score ??
            data.probability;

        const score =
            data.score ??
            data.posture_score ??
            data.postureScore;

        const status =
            data.status ??
            data.posture_status ??
            data.postureStatus ??
            "-";

        const correction =
            data.correction ??
            data.corrections ??
            data.feedback ??
            data.suggestions ??
            data.message ??
            "No correction suggestions were returned.";

        $("poseResult").textContent = String(pose);

        $("confidenceResult").textContent =
            confidence == null
                ? "-"
                : `${Number(confidence) <= 1
                    ? (Number(confidence) * 100).toFixed(1)
                    : Number(confidence).toFixed(1)}%`;

        $("scoreResult").textContent =
            score == null ? "-" : String(score);

        $("statusResult").textContent = String(status);
        $("postureStatusResult").textContent = String(status);

        $("correctionResult").textContent =
            Array.isArray(correction)
                ? correction.join(" ")
                : typeof correction === "object" && correction !== null
                    ? JSON.stringify(correction)
                    : String(correction);

        const resultImage = $("resultImage");

        const annotatedImage =
            data.image_url ??
            data.result_image ??
            data.annotated_image;

        if (annotatedImage && typeof annotatedImage === "string") {
            resultImage.src = annotatedImage;
            resultImage.hidden = false;
        } else {
            resultImage.hidden = true;
            resultImage.removeAttribute("src");
        }
    }

    // ---------------------------------------------------------
    // Initialize buttons
    // ---------------------------------------------------------

    function initializeAnalyzer() {
        const requiredElements = [
            "camera",
            "canvas",
            "startCameraBtn",
            "liveAnalysisBtn",
            "captureBtn",
            "stopCameraBtn",
            "cameraStatus",
            "cameraPlaceholder",
            "liveMessage",
            "imageInput",
            "uploadBtn",
            "uploadMessage",
            "uploadPreview",
            "uploadPreviewContainer",
            "removeImageBtn",
            "resultSection",
            "resultSource",
            "poseResult",
            "confidenceResult",
            "scoreResult",
            "statusResult",
            "postureStatusResult",
            "correctionResult",
            "resultImage"
        ];

        const missing = requiredElements.filter(id => !$(id));

        if (missing.length) {
            console.error("YogaFlow analyzer: missing HTML elements:", missing);
            return;
        }

        $("startCameraBtn").addEventListener("click", startCamera);
        $("liveAnalysisBtn").addEventListener("click", () => {
            if (liveAnalysisRunning) {
                stopLiveAnalysis();
            } else {
                startLiveAnalysis();
            }
        });

        $("captureBtn").addEventListener("click", captureAndAnalyze);
        $("stopCameraBtn").addEventListener("click", stopCamera);
        $("imageInput").addEventListener("change", handleImageSelection);
        $("uploadBtn").addEventListener("click", analyzeUploadedPhoto);
        $("removeImageBtn").addEventListener("click", removeSelectedImage);

        setCameraButtons(false);
        $("uploadBtn").disabled = true;

        console.log("YogaFlow analyzer initialized.");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initializeAnalyzer);
    } else {
        initializeAnalyzer();
    }
})();
