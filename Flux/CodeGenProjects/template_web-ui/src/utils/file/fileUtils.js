import { sha256 } from "js-sha256";

/**
 * @function computeFileChecksum
 * @description Computes the SHA-256 checksum of a given File object.
 * It prioritizes the native Web Crypto API (`crypto.subtle`) for performance,
 * and falls back to the `js-sha256` library if the native API is not available.
 * @param {File} file - The File object for which to compute the checksum.
 * @returns {Promise<string>} A promise that resolves with the hexadecimal SHA-256 checksum string.
 * @throws {Error} If an error occurs during file reading or checksum computation.
 */
export async function computeFileChecksum(file) {
    // Check if the Web Crypto API is supported by the browser.
    if (crypto.subtle) {
        // Use Web Crypto API if supported by the browser
        const arrayBuffer = await file.arrayBuffer();
        const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));  // Convert buffer to byte array
        const hashHex = hashArray.map((byte) => byte.toString(16).padStart(2, '0')).join('');
        return hashHex;
    } else {
        // Fallback to js-sha256 if Web Crypto API is not available.
        return new Promise((resolve, reject) => {
            const reader = new FileReader();

            reader.onload = (event) => {
                const fileData = event.target.result;
                const hash = sha256(fileData);
                resolve(hash);
            };

            reader.onerror = (err) => {
                const err_ = `Error occurred while reading file: ${err}`;
                console.error(err_);
                reject(new Error(err_)); // Reject with an Error object
            };

            reader.readAsArrayBuffer(file);
        });
    }
}