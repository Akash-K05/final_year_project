import React, { useState } from "react";
import axios from "axios";

const MedicineDetection = () => {
  const [imageFile, setImageFile] = useState(null);
  const [detection, setDetection] = useState(null);
  const [newName, setNewName] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState(null);

  const API_BASE_URL = "http://127.0.0.1:8080/api";

  // Handle file upload
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setImageFile(file);
    setPreview(URL.createObjectURL(file));
  };

  // Handle medicine detection request
  const handleUpload = async () => {
    if (!imageFile) {
      setStatusMessage("Please upload an image file.");
      return;
    }

    const formData = new FormData();
    formData.append("file", imageFile);

    try {
      setLoading(true);
      setStatusMessage("Processing image...");
      const response = await axios.post(`${API_BASE_URL}/detect`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      // The API now returns the detection object directly
      setDetection(response.data);
      setStatusMessage("Detection complete.");
    } catch (error) {
      setStatusMessage("Error occurred during medicine detection.");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // Update medicine name
  const handleUpdateName = async () => {
    if (!detection || !newName) {
      setStatusMessage("Please enter a new medicine name.");
      return;
    }

    try {
      const response = await axios.put(`${API_BASE_URL}/update-medicine-name`, {
        detection_id: detection.detection_id,
        new_name: newName,
      });

      if (response.data.success) {
        // Update local state with new medicine name
        setDetection({ ...detection, medicine_name: newName });
        setStatusMessage("Medicine name updated successfully.");
        
        // After updating name, fetch new composition and side effects
        const compositionResponse = await axios.get(
          `${API_BASE_URL}/get-medicine-info?medicine_name=${encodeURIComponent(newName)}`
        );
        
        if (compositionResponse.data) {
          setDetection({
            ...detection,
            medicine_name: newName,
            composition: compositionResponse.data.composition,
            side_effects: compositionResponse.data.side_effects,
          });
        }
        
        setNewName("");
      }
    } catch (error) {
      setStatusMessage("Failed to update medicine name.");
      console.error(error);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white rounded-lg shadow-lg">
      <h1 className="text-3xl font-semibold text-center text-gray-700 mb-6">
        Smart Drug Authentication
      </h1>

      {/* Upload File Section */}
      <div className="mb-6">
        <label className="block text-lg font-medium text-gray-600 mb-2">
          Upload Medicine Image
        </label>
        <input
          type="file"
          accept="image/*"
          onChange={handleFileChange}
          className="block w-full text-sm text-gray-500 border border-gray-300 rounded-lg p-2 mb-4"
        />
        {preview && <img src={preview} alt="Preview" className="w-64 mx-auto mt-4 rounded-lg shadow-md" />}
        <button
          onClick={handleUpload}
          disabled={loading}
          className="w-full py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition duration-200"
        >
          {loading ? "Detecting..." : "Detect Medicine"}
        </button>
      </div>

      {/* Status Message */}
      {statusMessage && <p className="text-center text-gray-600 mb-4">{statusMessage}</p>}

      {/* Display Detected Medicine Info */}
      {detection && (
        <div className="p-4 border border-gray-200 rounded-lg shadow-sm bg-gray-50">
          <h2 className="text-2xl font-semibold text-gray-700 mb-4">Detection Result</h2>
          <p className="font-medium text-gray-800">Medicine: {detection.medicine_name || "N/A"}</p>
          <p className="text-gray-600">Composition: {detection.composition || "Unknown"}</p>
          <p className="text-gray-600">Side Effects: {detection.side_effects || "Not Available"}</p>
          <p className={`text-lg font-bold ${detection.is_authentic ? "text-green-600" : "text-red-600"}`}>
            {detection.is_authentic ? "Authentic Drug ✅" : "Counterfeit Drug ❌"}
          </p>

          {/* Medicine Name Update Section */}
          <div className="mt-4">
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Enter new medicine name"
              className="block w-full p-2 border border-gray-300 rounded-lg"
            />
            <button
              onClick={handleUpdateName}
              className="mt-2 py-2 px-4 bg-green-600 text-white rounded-lg hover:bg-green-700 transition duration-200"
            >
              Update Name
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default MedicineDetection;