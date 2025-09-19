import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MediaCardBase from "@/app/components/MediaCard/MediaCardBase";
import type { DiscoverItem } from "@/app/lib/types";
import { renderWithProviders } from "@/app/test-utils";

const mutateAsync = vi.fn();
const navigateMock = vi.fn();
const toastSuccess = vi.fn();
const toastError = vi.fn();
const toastMock = Object.assign(vi.fn(), {
  success: toastSuccess,
  error: toastError,
});

vi.mock("sonner", () => ({
  toast: toastMock,
}));

vi.mock("@/app/lib/api", () => ({
  useMutateList: () => ({ mutateAsync }),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigateMock,
    useLocation: () => ({ pathname: "/movies" }),
  };
});

describe("MediaCardBase", () => {
  const item: DiscoverItem = {
    id: "123",
    kind: "movie",
    title: "Inception",
    year: 2010,
    subtitle: "Dream Heist",
    poster: "https://image.tmdb.org/t/p/original/inception.jpg",
    genres: ["Sci-Fi", "Thriller"],
    badges: ["HDR", "4K"],
    progress: 0.35,
    meta: { source: "tmdb" },
  };

  beforeEach(() => {
    mutateAsync.mockReset().mockResolvedValue(undefined);
    navigateMock.mockReset();
    toastMock.mockClear();
    toastSuccess.mockClear();
    toastError.mockClear();
  });

  it("renders media information and opens details when card clicked", async () => {
    const user = userEvent.setup();
    renderWithProviders(<MediaCardBase item={item} />);

    expect(screen.getByRole("heading", { name: item.title })).toBeInTheDocument();
    expect(screen.getByText("Sci-Fi, Thriller", { exact: false })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /details/i }));
    expect(navigateMock).toHaveBeenCalledWith(
      `/details/${item.kind}/${item.id}`,
      expect.objectContaining({
        state: { backgroundLocation: expect.objectContaining({ pathname: "/movies" }) },
      }),
    );
  });

  it("queues watchlist mutation and shows success toast", async () => {
    const user = userEvent.setup();
    renderWithProviders(<MediaCardBase item={item} />);

    await user.click(screen.getByRole("button", { name: /add to watchlist/i }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        action: "add",
        list: "watchlist",
        item: { id: item.id, kind: item.kind },
      });
    });

    expect(navigateMock).not.toHaveBeenCalled();
    expect(toastMock.success).toHaveBeenCalledWith(`Added ${item.title} to your watchlist.`);
  });
});
