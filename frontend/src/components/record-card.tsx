import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface RecordCardProps {
  title: string;
  description: string;
  actionText: string;
  footerText: string;
}

function RecordCard({
  title,
  description,
  actionText,
  footerText,
}: RecordCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
        <CardAction>{actionText}</CardAction>
      </CardHeader>
      <CardContent>
        <p>Card Content</p>
      </CardContent>
      <CardFooter>
        <p>{footerText}</p>
      </CardFooter>
    </Card>
  );
}

export default RecordCard;
