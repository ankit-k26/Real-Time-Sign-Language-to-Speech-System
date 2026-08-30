import { useEffect, useRef } from "react";

/**
 * Opens the webcam into `videoRef`, and every `intervalMs` grabs a frame,
 * encodes it as a JPEG data URL, and calls `onFrame(base64)`.
 * This replaces collect_data.py / gui.py's cv2.VideoCapture(0) loop.
 */
export function useWebcam(videoRef, onFrame, intervalMs = 150, active = true) {
  const streamRef = useRef(null);
  const canvasRef = useRef(document.createElement("canvas"));

  useEffect(() => {
    if (!active) return;
    let intervalId;

    navigator.mediaDevices
      .getUserMedia({ video: { width: 640, height: 480 } })
      .then((stream) => {
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        intervalId = setInterval(() => grabFrame(), intervalMs);
      })
      .catch((err) => console.error("Webcam access denied:", err));

    function grabFrame() {
      const video = videoRef.current;
      if (!video || video.readyState < 2) return;
      const canvas = canvasRef.current;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      ctx.translate(canvas.width, 0);
      ctx.scale(-1, 1); // mirror, matches cv2.flip(frame, 1) in the original
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL("image/jpeg", 0.7);
      onFrame(dataUrl.split(",")[1]);
    }

    return () => {
      clearInterval(intervalId);
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, [active, intervalMs]);
}
