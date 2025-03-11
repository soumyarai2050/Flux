import { sha256 } from "js-sha256";

export async function computeFileChecksum(file) {
    if (crypto.subtle) {
        // crypto API is supported by browser
        const arrayBuffer = await file.arrayBuffer();
        const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));  // Convert buffer to byte array
        const hashHex = hashArray.map((byte) => byte.toString(16).padStart(2, '0')).join('');
        return hashHex;
    } else {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();

            reader.onload = (event) => {
                const fileData = event.target.result;
                const hash = sha256(fileData);
                resolve(hash);
            }

            reader.onerror = (err) => {
                const err_ = `Error occurred while reading file: ${err}`;
                console.error(err_);
                reject();
            }

            reader.readAsArrayBuffer(file);
        })
    }
}