import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Upload as UploadIcon, FileUp } from "lucide-react";
import { useWallet } from "@/providers/wallet-provider";
import { useNavigate } from "react-router-dom";

function Upload() {
  const { isConnected } = useWallet();
  const navigate = useNavigate();

  if (!isConnected) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle>Connect Wallet Required</CardTitle>
            <CardDescription>
              You need to connect your wallet to upload and sell datasets.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => navigate("/")} className="w-full">
              Go to Home
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <div className="mx-auto w-full max-w-4xl px-4 py-12">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Sell Your Dataset</h1>
          <p className="text-muted-foreground">
            List your dataset with embeddings on the marketplace and earn ETH
            from sales.
          </p>
        </div>

        <form className="space-y-6">
          {/* Basic Information */}
          <Card>
            <CardHeader>
              <CardTitle>Basic Information</CardTitle>
              <CardDescription>
                Provide details about your dataset
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="title">Dataset Title</Label>
                <Input
                  id="title"
                  placeholder="e.g., UCI Heart Disease Dataset"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="Describe your dataset, its features, and potential use cases..."
                  rows={4}
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="price">Price (ETH)</Label>
                  <Input
                    id="price"
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="0.05"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="domain">Domain</Label>
                  <Input
                    id="domain"
                    placeholder="e.g., Healthcare, Finance"
                    required
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* File Upload */}
          <Card>
            <CardHeader>
              <CardTitle>Upload Files</CardTitle>
              <CardDescription>
                Upload your dataset and vector embeddings
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="csv-file">Dataset File (CSV/Parquet)</Label>
                <div className="border-2 border-dashed rounded-lg p-8 text-center hover:border-primary/50 transition-colors cursor-pointer">
                  <FileUp className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground mb-2">
                    Click to upload or drag and drop
                  </p>
                  <Input
                    id="csv-file"
                    type="file"
                    accept=".csv,.parquet"
                    className="hidden"
                  />
                  <Button type="button" variant="outline" size="sm">
                    Choose File
                  </Button>
                </div>
              </div>
              {/* <div className="space-y-2">
                <Label htmlFor="vector-file">Vector Embeddings (JSON)</Label>
                <div className="border-2 border-dashed rounded-lg p-8 text-center hover:border-primary/50 transition-colors cursor-pointer">
                  <FileUp className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground mb-2">
                    Click to upload or drag and drop
                  </p>
                  <Input
                    id="vector-file"
                    type="file"
                    accept=".json"
                    className="hidden"
                  />
                  <Button type="button" variant="outline" size="sm">
                    Choose File
                  </Button>
                </div>
              </div> */}
            </CardContent>
          </Card>

          {/* Vector Specification */}
          <Card>
            <CardHeader>
              <CardTitle>Vector Specification</CardTitle>
              <CardDescription>
                Provide details about your embeddings
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="embedding-model">Embedding Model</Label>
                  <Input
                    id="embedding-model"
                    placeholder="e.g., text-embedding-3-large"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="dimension">Dimension</Label>
                  <Input
                    id="dimension"
                    type="number"
                    placeholder="1536"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="distance-metric">Distance Metric</Label>
                  <Input
                    id="distance-metric"
                    placeholder="cosine, l2"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="rows">Number of Rows</Label>
                  <Input id="rows" type="number" placeholder="1000" required />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Submit */}
          <div className="flex justify-end gap-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => navigate("/")}
            >
              Cancel
            </Button>
            <Button type="submit" className="gap-2">
              <UploadIcon className="h-4 w-4" />
              List Dataset
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default Upload;
