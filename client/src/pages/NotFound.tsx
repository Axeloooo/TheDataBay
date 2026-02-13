import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";

function NotFound() {
  const navigate = useNavigate();
  return (
    <div className="min-h-[60vh] flex items-center justify-center px-4">
      <div className="w-full max-w-xl rounded-2xl border bg-card p-8 text-center shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Error 404
        </p>
        <h1 className="mt-2 text-3xl font-bold">Page Not Found</h1>
        <p className="mt-3 text-sm text-muted-foreground">
          The route you requested does not exist or may have been moved.
        </p>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
          <Button onClick={() => navigate("/")}>Go Home</Button>
          <Button variant="outline" onClick={() => navigate(-1)}>
            Go Back
          </Button>
        </div>
      </div>
    </div>
  );
}

export default NotFound;
