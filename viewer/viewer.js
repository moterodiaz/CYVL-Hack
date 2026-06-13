/**
 * APS Viewer initialization.
 *
 * Fetches a data:read token from the local token_server.py,
 * then loads the translated model by URN.
 */

// Set URN here after running the pipeline
const MODEL_URN = "YOUR_URN_HERE";

async function getToken(callback) {
  try {
    const resp = await fetch("/api/token");
    const data = await resp.json();
    callback(data.access_token, data.expires_in);
  } catch (err) {
    console.error("Token fetch failed:", err);
  }
}

function initViewer() {
  const options = {
    env: "AutodeskProduction2",
    api: "streamingV2",
    getAccessToken: getToken,
  };

  Autodesk.Viewing.Initializer(options, () => {
    const container = document.getElementById("viewer");
    const viewer = new Autodesk.Viewing.GuiViewer3D(container);
    viewer.start();

    const documentId = `urn:${MODEL_URN}`;
    Autodesk.Viewing.Document.load(
      documentId,
      (doc) => {
        const viewable = doc.getRoot().getDefaultGeometry();
        if (viewable) {
          viewer.loadDocumentNode(doc, viewable);
        } else {
          console.warn("No viewable geometry found in the model.");
        }
      },
      (code, message) => {
        console.error(`Document load failed [${code}]: ${message}`);
      }
    );
  });
}

// Auto-start
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initViewer);
} else {
  initViewer();
}
