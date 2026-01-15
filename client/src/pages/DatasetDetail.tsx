import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
import RecordCardDetails from "@/components/record-card-details";
import { MOCK_DATASETS } from "@/mocks/datasets";

function DatasetDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const dataset = MOCK_DATASETS.find((d) => d.id === id);

  if (!dataset) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-2">Dataset Not Found</h1>
          <p className="text-muted-foreground mb-4">
            The dataset you're looking for doesn't exist.
          </p>
          <Button onClick={() => navigate("/")}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Marketplace
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <div className="mx-auto w-full max-w-4xl px-4 py-6">
        <Button
          variant="ghost"
          onClick={() => navigate("/")}
          className="mb-4 gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Marketplace
        </Button>
        <RecordCardDetails dataset={dataset} isPurchased={false} />
      </div>
    </div>
  );
}

export default DatasetDetail;
