###  API Documentation (Python Similarity Check)

---
<br/>

### **1. Match File**
- **Endpoint:** `/match-file`
- **Method:** `POST`
- **Description:** Upload an Excel file and perform fuzzy matching of compositions. The file can either be a normal price bid file or an implant price bid file, determined by the `file_type`.
- **Request:**
  - **Content-Type:** `multipart/form-data`
  - **Parameters:**
    - `file`: The Excel file containing compositions to match.
    - `file_type` (optional): Integer to specify the type of file (`1` for Normal Price Bid File, `2` for Implant Price Bid File). Defaults to `1`.
- **Response:**
  - **Success:**
    - **Status:** `200 OK`
    - **Body:** JSON object containing `matched` and `unmatched` compositions.
  - **Error:**
    - **Status:** `400 Bad Request`: If no file is uploaded or if an invalid file type is provided.
    - **Status:** `500 Internal Server Error`: If there's an error processing the file or matching compositions.

---
<br/>

## Composition Routes

### **2. Compare Price for Similar Items**
- **Endpoint:** `/similar-items/compare-price`
- **Method:** `POST`
- **Description:** Compare the price of a composition with a similar item from the `PriceCap` table.
- **Request:**
  - **Content-Type:** `application/json`
  - **Parameters:**
    - `similar_composition_id`: ID of the similar composition.
    - `composition`: Object containing the details of the composition.
    - `similar_item`: Name of the similar item to compare.
- **Response:**
  - **Success:**
    - **Status:** `200 OK`
    - **Body:** JSON object with price comparison details.
  - **Error:**
    - **Status:** `400 Bad Request`: If `composition` or `similar_item` is missing.
    - **Status:** `500 Internal Server Error`: If there's an error during price comparison.

---

### **3. Get All Compositions**
- **Endpoint:** `/get-all-compositions`
- **Method:** `GET`
- **Description:** Retrieve all compositions from the database with optional pagination and search functionality.
- **Request:**
  - **Query Parameters:**
    - `page` (optional): Page number for pagination. Defaults to `1`.
    - `search_keyword` (optional): Search keyword to filter compositions.
- **Response:**
  - **Success:**
    - **Status:** `200 OK`
    - **Body:** JSON object containing `approved` and `pending` compositions, with counts and details.
  - **Error:**
    - **Status:** `500 Internal Server Error`: If there's an error retrieving compositions.

---

### **4. Add New Composition**
- **Endpoint:** `/add-new-composition`
- **Method:** `POST`
- **Description:** Add a new composition with approver status (`status=1`).
- **Request:**
  - **Content-Type:** `application/x-www-form-urlencoded`
  - **Parameters:**
    - `content_code` (optional): Code associated with the composition.
    - `composition_name` (required): Name of the composition.
    - `dosage_form` (optional): Dosage form of the composition.
- **Response:**
  - **Success:**
    - **Status:** `200 OK`
    - **Body:** JSON object with a success message.
  - **Error:**
    - **Status:** `400 Bad Request`: If `composition_name` is missing.
    - **Status:** `500 Internal Server Error`: If there's an error adding the composition.

---

### **5. Get Composition by ID**
- **Endpoint:** `/get-composition/<int:composition_id>`
- **Method:** `GET`
- **Description:** Fetch details of a composition by its ID.
- **Response:**
  - **Success:**
    - **Status:** `200 OK`
    - **Body:** JSON object with composition details.
  - **Error:**
    - **Status:** `404 Not Found`: If no composition is found with the provided ID.
    - **Status:** `500 Internal Server Error`: If there's an error retrieving the composition.

---

### **6. Update Composition**
- **Endpoint:** `/update-composition/<int:composition_id>`
- **Method:** `PUT`
- **Description:** Update an existing composition.
- **Request:**
  - **Content-Type:** `application/x-www-form-urlencoded`
  - **Parameters:**
    - `content_code` (optional): Code associated with the content.
    - `composition_name` (optional): Name of the composition.
    - `dosage_form` (optional): Dosage form of the composition.
- **Response:**
  - **Success:**
    - **Status:** `200 OK`
    - **Body:** JSON object with a success message.
  - **Error:**
    - **Status:** `404 Not Found`: If no composition is found to update.
    - **Status:** `500 Internal Server Error`: If there's an error updating the composition.

---

### **7. Delete Composition**
- **Endpoint:** `/delete-composition/<int:composition_id>`
- **Method:** `DELETE`
- **Description:** Delete a composition by its ID.
- **Response:**
  - **Success:**
    - **Status:** `200 OK`
    - **Body:** JSON object with a success message.
  - **Error:**
    - **Status:** `404 Not Found`: If no composition is found to delete.
    - **Status:** `500 Internal Server Error`: If there's an error deleting the composition.

---

### **8. Request Composition**
- **Endpoint:** `/request-composition`
- **Method:** `POST`
- **Description:** Request a new composition with a pending approval status (`status=0`).
- **Request:**
  - **Content-Type:** `application/x-www-form-urlencoded`
  - **Parameters:**
    - `content_code` (optional): Code associated with the composition.
    - `composition_name` (required): Name of the composition.
    - `dosage_form` (optional): Dosage form of the composition.
- **Response:**
  - **Success:**
    - **Status:** `200 OK`
    - **Body:** JSON object with a success message and `status=0`.
  - **Error:**
    - **Status:** `400 Bad Request`: If `composition_name` is missing.
    - **Status:** `500 Internal Server Error`: If there's an error requesting the composition.

---

### **9. Approve Composition**
- **Endpoint:** `/approve-composition`
- **Method:** `POST`
- **Description:** Approve a composition by updating its status to `1`.
- **Request:**
  - **Content-Type:** `application/json`
  - **Parameters:**
    - `composition_id` (required): ID of the composition to approve.
- **Response:**
  - **Success:**
    - **Status:** `200 OK`
    - **Body:** JSON object with a success message and `status=1`.
  - **Error:**
    - **Status:** `400 Bad Request`: If `composition_id` is missing.
    - **Status:** `500 Internal Server Error`: If there's an error approving the composition.


---

<br/>

## Implant Routes

### **10. Compare Price for Similar Items**


- **Endpoint:** `/similar-items-implants/compare-price`
- **Method:** `POST`
- **Description:** Compares the price of a specified implant with similar items, fetching relevant price information from the price cap system.

- **Request Body:**
  - `similar_implant_id` (int, required): The ID of the similar implant being compared.
  - `implant` (object, required): The implant object with attributes including `df_unit_rate_to_hll_excl_of_tax`.
  - `similar_item` (string, required): The description of the similar implant to be compared.



- **Response:**
  - **Success:**: JSON object with the price comparison result.
  - **Error:**: JSON object with an error message.



- **Error Codes:**
  - `400`: Implant object or similar Implant Id is missing from the request.
  - `500`: Internal server error during price comparison.

---
