import RecordCard from "@/components/record-card";
import { MOCK_DATASETS } from "@/mocks/datasets";
import type { DatasetRecord } from "@/types/dataset";

function Home() {
  return (
    <div className="min-h-screen">
      <div className="mx-auto w-full max-w-6xl px-4 py-6">
        <div className="grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {MOCK_DATASETS.map((dataset: DatasetRecord) => (
            <RecordCard
              key={dataset.id}
              id={dataset.id}
              title={dataset.title}
              description={dataset.description}
              priceEth={dataset.priceEth}
              rows={dataset.rows}
              columns={dataset.columns}
              dimension={dataset.vectorSpec.dimension}
              verified={dataset.verified}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export default Home;
