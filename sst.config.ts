/// <reference path="./.sst/platform/config.d.ts" />

export default $config({
  app(input) {
    return {
      name: "gemini-trail",
      removal: input?.stage === "production" ? "retain" : "remove",
      home: "aws",
    };
  },
  async run() {
    // 1. Deploy the FastAPI Python Backend onto AWS Lambda
    const backendApi = new sst.aws.Function("FastApiBackend", {
      handler: "backend/main.handler", // Points to backend/main.py -> handler variable
      runtime: "python3.11",
      url: true, // Provisions a FREE live URL directly from Lambda
      environment: {
        GEMINI_API_KEY: process.env.GEMINI_API_KEY || "",
      },
    });

    // 2. Deploy the Next.js Frontend App
    const frontendWeb = new sst.aws.Nextjs("NextJsFrontend", {
      path: "frontend", // Points to your frontend directory
      domain: {
        name: "nauticaltrail.com", // Porkbun domain
        dns: false                 // Manually managing DNS records in Porkbun
      },
      environment: {
        // Automatically injects the Lambda URL directly into your NextJS environment variables!
        NEXT_PUBLIC_API_URL: backendApi.url,
      },
    });

    // Output the static distribution links to your terminal & GitHub logs
    return {
      frontendUrl: frontendWeb.url,
      backendUrl: backendApi.url,
    };
  },
});
