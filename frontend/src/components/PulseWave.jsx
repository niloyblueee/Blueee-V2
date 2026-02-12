export default function PulseWave({ active }) {
  return (
    <div className="flex items-end gap-2">
      {[0, 1, 2, 3, 4].map((index) => (
        <div
          key={index}
          className={`pulse-bar h-6 w-2 rounded-full bg-plasma ${
            active ? "opacity-100" : "opacity-40"
          }`}
        />
      ))}
    </div>
  );
}
