import Image from "next/image";

export default function Header() {
  return (
    <header className="flex h-20 items-center px-6 bg-white border-b">
        <div className="flex items-center gap-4">
            <Image
              src="https://pbs.twimg.com/media/G2bXov8XYAEyXj-?format=png&name=small"
              alt="StratoForce Logo"
              width={40}
              height={40}
              className="h-10 w-auto"
            />
            <h1 className="text-2xl font-bold tracking-tight font-headline text-black">
                &#123; stratoforce &#125;
            </h1>
        </div>
    </header>
  );
}
