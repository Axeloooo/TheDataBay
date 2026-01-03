import RecordCard from "@/components/record-card";

const data = [
  {
    title: "Record 1",
    description: "This is the first record.",
    actionText: "View Details",
    footerText: "Last updated 2 hours ago",
  },
  {
    title: "Record 2",
    description: "This is the second record.",
    actionText: "View Details",
    footerText: "Last updated 1 day ago",
  },
  {
    title: "Record 3",
    description: "This is the first record.",
    actionText: "View Details",
    footerText: "Last updated 2 hours ago",
  },
  {
    title: "Record 4",
    description: "This is the second record.",
    actionText: "View Details",
    footerText: "Last updated 1 day ago",
  },
  {
    title: "Record 5",
    description: "This is the first record.",
    actionText: "View Details",
    footerText: "Last updated 2 hours ago",
  },
  {
    title: "Record 6",
    description: "This is the second record.",
    actionText: "View Details",
    footerText: "Last updated 1 day ago",
  },
  {
    title: "Record 7",
    description: "This is the first record.",
    actionText: "View Details",
    footerText: "Last updated 2 hours ago",
  },
  {
    title: "Record 8",
    description: "This is the second record.",
    actionText: "View Details",
    footerText: "Last updated 1 day ago",
  },
];

function Home() {
  return (
    <div className="min-h-screen">
      <div className="mx-auto w-full max-w-6xl px-4 py-6">
        <div className="grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {data.map((record, index) => (
            <RecordCard
              key={index}
              title={record.title}
              description={record.description}
              actionText={record.actionText}
              footerText={record.footerText}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export default Home;
