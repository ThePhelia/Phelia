import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import FiltersBar from "@/app/components/FiltersBar";
import type { DiscoverParams } from "@/app/lib/types";
import { renderWithProviders } from "@/app/test-utils";

describe("FiltersBar", () => {
  const baseFilters: DiscoverParams & { search?: string } = {
    sort: "trending",
    search: "",
  };

  it("updates search and sort filters", async () => {
    let currentFilters = { ...baseFilters };
    const onChange = vi.fn();
    const user = userEvent.setup();

    const { rerender } = renderWithProviders(
      <FiltersBar kind="movie" filters={currentFilters} onChange={onChange} />,
    );

    onChange.mockImplementation((next) => {
      currentFilters = { ...currentFilters, ...next };
      rerender(<FiltersBar kind="movie" filters={currentFilters} onChange={onChange} />);
    });

    const searchInput = screen.getByPlaceholderText(/search movies/i);
    await user.type(searchInput, "Matrix");

    expect(onChange).toHaveBeenCalled();
    expect(onChange).toHaveBeenLastCalledWith({ search: "Matrix" });

    onChange.mockClear();

    await user.click(screen.getByRole("button", { name: /sort: trending/i }));
    await user.click(screen.getByRole("button", { name: "Popular" }));

    expect(onChange).toHaveBeenLastCalledWith({ sort: "popular" });
  });

  it("resets filters including music specific options", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    const filters: DiscoverParams & { search?: string } = {
      ...baseFilters,
      genre: "Rock",
      year: "2022",
      type: "album",
      search: "Daft",
    };

    renderWithProviders(<FiltersBar kind="music" filters={filters} onChange={onChange} />);

    await user.click(screen.getByRole("button", { name: /type: album/i }));
    await user.click(screen.getByRole("button", { name: "EP" }));

    expect(onChange).toHaveBeenLastCalledWith({ type: "ep" });

    await user.click(screen.getByRole("button", { name: /reset/i }));

    expect(onChange).toHaveBeenLastCalledWith({
      search: "",
      genre: undefined,
      year: undefined,
      sort: "trending",
      type: undefined,
    });
  });
});
